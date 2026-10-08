# Email OTP and Google Sign-In Setup

## Email OTP with Gmail

1. Turn on 2-Step Verification for the Gmail account that will send the codes.
2. Create a Google App Password for that Gmail account.
3. Open PowerShell in the project folder.
4. Set these values before starting Django:

```powershell
$env:EMAIL_HOST="smtp.gmail.com"
$env:EMAIL_PORT="587"
$env:EMAIL_HOST_USER="yourgmail@gmail.com"
$env:EMAIL_HOST_PASSWORD="your-16-character-app-password"
$env:EMAIL_USE_TLS="True"
$env:DEFAULT_FROM_EMAIL="yourgmail@gmail.com"
```

5. Start the project with `python manage.py runserver`.
6. Register with the user's real email address.
7. The 6-digit OTP is sent to that email address.
8. The code expires after 10 minutes.
9. If the code is wrong or expired, use **Resend OTP**.

If the email settings are not configured, Django uses the console email backend and prints the OTP in the terminal for local testing.

## Google Sign-In

1. Open Google Cloud Console.
2. Create or select a project.
3. Enable the Google identity/OAuth service.
4. Create an OAuth 2.0 Client ID for a Web Application.
5. Add this authorized redirect URI:

`http://127.0.0.1:8000/accounts/google/callback/`

6. Set these PowerShell values:

```powershell
$env:GOOGLE_CLIENT_ID="your-client-id"
$env:GOOGLE_CLIENT_SECRET="your-client-secret"
$env:GOOGLE_REDIRECT_URI="http://127.0.0.1:8000/accounts/google/callback/"
```

7. Restart Django.
8. Click **Continue with Google**.
9. Google opens the account-selection screen.
10. A verified Google email can create a new Tenant account or sign in to an existing account with the same email.
