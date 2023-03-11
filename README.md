# Download zoom recordings and save to Google Drive

This script supports downloading Zoom recordings, and upload these files to specified Goolge Drive folder.

## Setup

### Download credentials.json from Google Cloud Console.

Enable Google Drive API via Google Cloud console, then place credentials file as `credentials.json`.

1. Go to the Google Cloud Console (https://console.cloud.google.com/).
2. Click the "Select a project" drop-down list at the top of the screen and select the project you want to use.
3. Click the navigation menu (≡) in the top-left corner of the screen, then select "APIs & Services" > "Library".
4. Search for "Google Drive API" and click on it.
5. Click the "Enable" button to enable the API.
6. Once the API is enabled, click on "Credentials" in the left navigation menu.
7. Click the "Create credentials" button and select "OAuth client ID".
8. Select "Desktop app" or "Other non-UI" as the application type, then give your OAuth client ID a name.
9. Click "Create" and follow the prompts to complete the OAuth client ID setup.
10. After creating the OAuth client ID, you will be able to access the credentials page again and download the client ID and client secret for your application.
11. Move the downloaded json file to the root folder of this application and named `credentials.json`.

### Create Zoom App and create `zoom_credentials.json`

1. Go to the Zoom App Marketplace (https://marketplace.zoom.us/).
2. Click the "Develop" dropdown menu in the top-right corner of the screen, then select "Build App".
3. Select "OAuth" as the app type and click "Create".
4. Enter a name for your app and Account-level app, click "Create".
5. On the "App Credentials" page, you will find your "Client ID" and "Client Secret". Save this information as you will need this information later.
6. In the "Redirect URL for OAuth" section, add `http://localhost:8080/`.
7. In the "Add allow lists" section, add `http://localhost:8080/`.
8. In the "Basic Information" section, add your app's description, logo, and other relevant details.
9. In the "Feature" section, you don't need to select features.
10. In the "Scopes" section, click `Add Scopes` and select the scope `View your recordings (recording:read)`.
11. Click "Save" to save your changes.
12. Copy `zoom_credentials.json.example` as `zoom_credentials.json`, then edit `YOUR_CLIENT_ID` and `YOUR_CLIENT_SECRET` by the information obtained by step 5.

### Install requirements

The tested python version is `3.10.6`

Run
`pip install -r requirements.txt`

### Run script

`python save.py {googledrive_folder_id}`

You can get the googledrive_folder_id from the Google Dfive URL.

Example: https://drive.google.com/drive/u/1/folders/**1N3xbtEKMhDsarV5PO-H-2argObRpsfdie3**

(The string after `/folders/` is the id.)
