import os
import sys
import requests
import json
import httplib2
import datetime
import urllib
import pytz
from tqdm import tqdm
from dotenv import load_dotenv

from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import argparser, run_flow

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.http import MediaFileUpload

SCOPES = ['https://www.googleapis.com/auth/drive']


def downloadfile(fileurl, localpath, filesize, headers):
    """
    Download file from the url

    Parameters:
    fileurl (str): the url of downloading file
    localpath (str): the path to save downloaded file
    filesize int: filesize
    headers: the header sending to the url (used for authentication)

    Returns:
    None
    """
    with open(localpath, 'wb') as file:
        pbar = tqdm(total=filesize, unit='B', unit_scale=True)
        for chunk in requests.get(fileurl, stream=True,
                                  headers=headers).iter_content(
          chunk_size=1024):
            file.write(chunk)
            pbar.update(len(chunk))
        pbar.close()


def adjust_timezone(datetimestr, timezone):
    """
    Adjust timezone and return formatted date time.

    Parameters:
    datetimestr (str): the datetime formatted '%Y-%m-%dT%H:%M:%SZ'
    timezone (str): Tiemzone, ex. 'Asia/Tokyo'

    Returns:
    str: adjusted timestring '%Y-%m-%d %H:%M:%S'
    """
    # Define the original datetime object
    original_dt = datetime.datetime.strptime(datetimestr, '%Y-%m-%dT%H:%M:%SZ')

    # Define the timezone you want to convert to
    new_tz = pytz.timezone(timezone)

    # Convert the datetime object to the new timezone
    new_dt = original_dt.replace(tzinfo=pytz.utc).astimezone(new_tz)

    # Print the new datetime object with the new timezone
    return new_dt.strftime('%Y-%m-%d %H:%M:%S')


def get_selected_meetings(meetings):
    """
    Print selectable meeting list and return user selections

    Parameters:
    meetings (array): The array of meeting list obtained from Zoom API.

    Returns:
    array: selected meeting list
    """

    # Print the names of the meetings with letters for multiple choice
    for i, meeting in enumerate(meetings):
        print(f"{chr(i+97)}. {meeting['topic']} (",
              adjust_timezone(meeting['start_time'], meeting['timezone']),
              ")")

    # Collect user's selection
    selections = []
    while True:
        try:
            selection = input("Enter every letters of the meetings you'd"
                              " like to select: ").lower().replace(" ", "")
            if not selection:
                print("Please select at least one meeting.")
            else:
                for letter in selection:
                    index = ord(letter) - 97
                    if index < 0 or index >= len(meetings):
                        print(f"Invalid selection '{letter}'."
                              "Please try again.")
                        selections = []
                        break
                    else:
                        selections.append(meetings[index])
                if selections:
                    break
        except ValueError:
            print("Invalid selection. Please try again.")

    # Print the selected meetings
    print("You selected:")
    for meeting in selections:
        print(f"- {meeting['topic']} (",
              adjust_timezone(meeting['start_time'], meeting['timezone']),
              ")")
    return selections


def get_google_drive_folder_id():
    load_dotenv()
    if len(sys.argv) < 2:
        google_drive_folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
        if (not google_drive_folder_id):
            print("Please provide Google drive folder ID.")
            print("Usage: python save.py google_drive_folder_id")
            sys.exit(1)
    else:
        google_drive_folder_id = sys.argv[1]
    return google_drive_folder_id


def get_google_drive_credentials():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json')
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow\
                .from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return creds


def get_zoom_credentials(zoom_secrets_file):
    flow = flow_from_clientsecrets(zoom_secrets_file, 
                                   message='Please set up oauth first',
                                   scope=['recording:read'])
    storage = Storage("zoom_token.json")
    credentials = storage.get()
    if credentials is None or credentials.invalid:
        flags = argparser.parse_args()
        credentials = run_flow(flow, storage, flags)
    else:
        credentials.refresh(httplib2.Http())
    return credentials


def get_zoom_headers(zoom_credentials):
    return {'Authorization': f'Bearer {zoom_credentials.access_token}'}


def get_meetings_since(zoom_headers, since_date):
    zoom_api_url = 'https://api.zoom.us/v2/users/me/recordings?'
    query_string = urllib.parse.urlencode(
        {'from': since_date.strftime('%Y-%m-%d')})
    response = requests.get(zoom_api_url + query_string, headers=zoom_headers)
    response_data = json.loads(response.text)
    if 'meetings' not in response_data:
        print('There are no recent meetings.')
        sys.exit()
    return response_data['meetings']


def main():
    google_drive_folder_id = get_google_drive_folder_id()
    google_drive_creds = get_google_drive_credentials()
    zoom_secrets_file = "zoom_credentials.json"
    zoom_credentials = get_zoom_credentials(zoom_secrets_file)
    zoom_headers = get_zoom_headers(zoom_credentials)
    four_weeks_ago = datetime.date.today() - datetime.timedelta(days=28)
    meetings = get_meetings_since(zoom_headers, four_weeks_ago)
    selected_meetings = get_selected_meetings(meetings)

    # Download the recordings and save to Google Drive
    for meeting in selected_meetings:
        # Download only MP4 files
        if meeting['recording_files'][0]['status'] == 'processing':
            print('  Zoom is still processing recordings...')

        for recording in list(filter(lambda r: r['file_type'] == 'MP4', 
                                     meeting['recording_files'])):
            download_url = recording['download_url']
            file_name = f"{meeting['topic']} - "\
                "{recording['recording_start'].replace(':', '-')}.mp4"
            
            file_path = os.path.join(os.getcwd(), 'downloads', file_name)

            # Download
            print(f'Downloading {file_name}')
            downloadfile(download_url, file_path, recording['file_size'],
                         zoom_headers)

            # Upload the recording to Google Drive
            drive_service = build('drive', 'v3', 
                                  credentials=google_drive_creds)
            file_metadata = {'name': file_name, 
                             'parents': [google_drive_folder_id]}
            media = MediaFileUpload(file_path, resumable=True)
            print('Uploading downloaded file to Google Drive...')
            file = drive_service.files()\
                .create(body=file_metadata, media_body=media, fields='id',
                        supportsAllDrives=True).execute()

            # Print the Google Drive file ID
            print(f'Uploaded file ID: {file.get("id")}')
            print('Open file ', f'https://drive.google.com/file/d/{file.get("id")}/view')
    # finished!
    print('Finished')


if __name__ == '__main__':
    main()
