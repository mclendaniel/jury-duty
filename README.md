# Jury Duty Status Checker

Automated checker for Alameda County jury duty, group 143.

Fetches the [jury reporting page](https://www.alameda.courts.ca.gov/juryreporting) and sends a push notification via [ntfy.sh](https://ntfy.sh).

## Setup

1. Install dependencies:
   ```
   pip install requests beautifulsoup4
   ```

2. Install the **ntfy** app on your phone and subscribe to topic `morgan-jury-duty-143`:
   - [iOS](https://apps.apple.com/us/app/ntfy/id1625396347)
   - [Android](https://play.google.com/store/apps/details?id=io.heckel.ntfy)

3. Test:
   ```
   python3 check.py
   ```

4. Schedule via cron (5:05 PM Mon–Thu through March 12):
   ```
   crontab -e
   # Add:
   5 17 9-12 3 1-4 cd /Users/morganclendaniel/projects/jury-duty && /usr/bin/python3 check.py
   ```
