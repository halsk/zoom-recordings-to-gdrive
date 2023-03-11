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


def get_selected_meetings(mlist):
    """
    Print selectable meeting list and return user selections

    Parameters:
    mlist (array): The array of meeting list obtained from Zoom API.

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


SCOPES = ['https://www.googleapis.com/auth/drive']
load_dotenv()

# get folder id
if len(sys.argv) < 2:
    google_drive_folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
    if (not google_drive_folder_id):
        print("Please provide Google drive folder ID.")
        print("Usage: python save.py google_drive_folder_id")
        sys.exit(1)
else:
    google_drive_folder_id = sys.argv[1]

# Set up the Zoom API and Google Drive API credentials
print(google_drive_folder_id)
ZOOM_SECRETS_FILE = "zoom_credentials.json"

creds = None

if os.path.exists('token.json'):
    # get token from OAuth URL
    creds = Credentials.from_authorized_user_file('token.json')

if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        # refresh token
        creds.refresh(Request())
    else:
        # Open browser to get permission
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)
    with open('token.json', 'w') as token:
        # save token data to a file
        token.write(creds.to_json())

# Authenticate with the Zoom API using OAuth
flow = flow_from_clientsecrets(ZOOM_SECRETS_FILE,
                               message='Please set up oauth first',
                               scope=['recording:read'])
# read existing tokens
storage = Storage("zoom_token.json")
credentials = storage.get()

if credentials is None or credentials.invalid:
    # Open browser and get authentication.
    flags = argparser.parse_args()
    credentials = run_flow(flow, storage, flags)
else:
    # Make sure we have an up-to-date copy of the creds.
    credentials.refresh(httplib2.Http())

# Set access taken to a request header
zoom_headers = {
    'Authorization': f'Bearer {credentials.access_token}'
}

# get the date of four week before
today = datetime.date.today()
four_week_ago = today - datetime.timedelta(days=28)

# get recordings metadata
zoom_api_url = 'https://api.zoom.us/v2/users/me/recordings?'
print(zoom_api_url + urllib.parse.urlencode(
    {'from': four_week_ago.strftime('%Y-%m-%d')}))
response = requests.get(zoom_api_url + urllib.parse.urlencode(
    {'from': four_week_ago.strftime('%Y-%m-%d')}), headers=zoom_headers)
response_data = json.loads(response.text)

if 'meetings' not in response_data:
    # there is no meeting
    print('there is no meetings recently')
    sys.exit()

# user select which meeting should be recorded
meetings = response_data['meetings']
save_meeting_ids = get_selected_meetings(meetings)

# Download the recordings and save to Google Drive
for meeting in save_meeting_ids:
    # download only MP4 files
    for recording in list(filter(lambda r: r['file_type'] == 'MP4', 
                                 meeting['recording_files'])):
        download_url = recording['download_url']
        file_name = (
            f"{meeting['topic']} - "
            f"{recording['recording_start'].replace(':', '-')}.mp4"
        )
        file_path = os.path.join(os.getcwd(), 'downloads', file_name)
        # download
        print(f'Downloading {file_name}')
        downloadfile(download_url, file_path, recording['file_size'],
                     zoom_headers)

        # Upload the recording to Google Drive
        drive_service = build('drive', 'v3', credentials=creds)
        file_metadata = {'name': file_name,
                         'parents': [google_drive_folder_id]}
        media = MediaFileUpload(file_path, resumable=True)
        print('Uploading downloaded file to Google Drive...')
        file = drive_service.files().create(body=file_metadata,
                                            media_body=media, fields='id'
                                            ).execute()

        # Print the Google Drive file ID
        print(f'Uploaded file ID: {file.get("id")}')
# finished!
print('Finished')
