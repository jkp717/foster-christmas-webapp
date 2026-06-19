# Security Update — Deployment Notes

This release adds admin authentication and fixes several issues found in review.
Read this before deploying.

## What changed

1. **Admin login (Flask-Login).** The entire `/admin` area now requires signing
   in. A single shared admin account is configured from environment variables.
   Anonymous visitors are redirected to `/admin/login`.

2. **Public registration hardened.** The child-registration delete now requires
   a POST (no more delete-by-URL), and a foster family can no longer view or
   modify another family's child records by changing the ID in the URL
   (ownership is checked).

3. **SQL injection surface removed.** All raw f-string SQL in the model event
   handlers is now parameterized.

4. **CSRF protection.** Enabled app-wide (Flask-WTF). All forms (admin and the
   public registration/donation forms) carry CSRF tokens.

5. **Session cookies hardened.** HttpOnly + SameSite=Lax always; Secure (HTTPS
   only) in production; admin sessions expire after 12 hours.

6. **Rate limiting.** The login route and the public form endpoints
   (registration, sponsor, sponsor-request, donate) are rate-limited to slow
   brute-force and spam.

## One-time setup on deploy

1. Install the new dependencies:

       pip install -r requirements.txt

   (Adds Flask-Login, Flask-WTF, Flask-Limiter.)

2. Create the admin password hash (you'll be prompted for the password; it is
   never stored in plaintext):

       python cli.py create-admin-hash

3. Put the printed value, plus a username, in your `.env`:

       ADMIN_USERNAME=your_admin_name
       ADMIN_PASSWORD_HASH=<the hash printed above>

   Make sure `SECRET_KEY` is already set to a strong random value (it signs the
   login session and CSRF tokens).

4. Restart the app.

5. Visit `/admin` — you should be redirected to `/admin/login`. Sign in, confirm
   you reach the admin, then use **Sign Out** (top-right of the admin reports
   page) to confirm logout works.

## Removing the old nginx basic auth

Once Flask-Login is confirmed working, you can remove the old nginx HTTP basic
auth on `/admin` (the `auth_basic` / `auth_basic_user_file` directives). It is no
longer needed, and leaving it means two password prompts. Reload nginx after
editing.

## Notes / future hardening

- The rate limiter uses in-memory storage, which resets on restart and is
  per-process. If you ever run multiple worker processes, move it to Redis so
  limits are shared. For a single-worker deploy this is fine.
- Public registration remains open by design (foster parents self-register
  without accounts). The IDOR and GET-delete fixes reduce the risk; if you later
  want stronger protection, consider per-family access tokens.
- Confirm the site is served over HTTPS with an HTTP->HTTPS redirect, or the
  Secure cookie flag will prevent the admin session cookie from being sent.
