from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

CLIENT_ID = '605984988638-p4ohcgbh6ll223ku5l7m10a0fnkv9dm9.apps.googleusercontent.com'
CLIENT_SECRET = 'U_7UhjgKHX-_2u1Mqes9UnUA'
SCOPES = ['https://www.googleapis.com/auth/cloud-platform']

flow = InstalledAppFlow.from_client_secrets_file(
    'client_secret.json', scopes=SCOPES)
creds = flow.run_local_server(port=0)

refresh_token = creds.refresh_token
print( refresh_token )

# Save the refresh token to a file or database

