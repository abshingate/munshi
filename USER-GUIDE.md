# Your Accounting Computer — Simple Guide

*(Give this file to the person who will use the machine. No computer expertise needed.)*

## What is this?

You have a **Windows computer that lives on the internet** (in Amazon's data
center in Mumbai). Tally and everything you need for GST, PF, PT and Income-tax
work is already on it.

Think of it like a shop you rent by the hour:

- When you **turn it on**, you pay about **Rs. 12 per hour**.
- When you **turn it off**, you pay almost nothing (about Rs. 750/month just to
  keep your data safe).
- **Nothing is ever lost** when you turn it off. Your Tally data, your files,
  your bookmarks — everything is exactly where you left it, and a backup copy
  is taken automatically every night at 2 AM.

## Setting up a new Mac (one time only)

Got this folder on a new Mac (or setting up for the first time)? Double-click
**`0 - First Time Setup (run once)`** and follow what it says. It installs
everything needed by itself. It will ask you for at most three things:

1. Your **Mac login password** (typing is invisible — that's normal).
2. Your **two AWS keys** — ask whoever manages your AWS account for an
   "Access Key ID" and "Secret Access Key".
3. Your **email** for warning messages.

It's safe to run again any time — it skips what's already done.

*If the Mac complains the button "can't be opened because it is from an
unidentified developer": don't worry — right-click (or hold Control and click)
the button and choose **Open**. You only have to do this once per button.*

- If this folder was **copied from another computer**, it just connects and
  you're done.
- If this is a **brand-new setup**, it asks before creating the cloud computer
  (and tells you the cost first).

## No Mac? Set it up entirely in the browser

You can create the cloud computer without installing ANYTHING on any computer,
using a terminal that lives inside the AWS website itself:

1. Log in to **aws.amazon.com**. In the top-right corner, set the region to
   **Mumbai (ap-south-1)**.
2. Click the **CloudShell icon** in the top bar (it looks like `>_`).
   A black window opens at the bottom — that's a computer AWS gives you for
   free, already logged in to your account.
3. In that window's menu click **Actions → Upload file** and upload the
   `TallyCloud-new.zip` file you were given.
4. Copy-paste these two lines and press Enter:

       unzip -o TallyCloud-new.zip -d tally && cd tally
       bash scripts/cloudshell-deploy.sh

5. Answer its questions (it tells you exactly where to find each answer) and
   it builds everything, then prints your address, and how to get the password.

After that, day-to-day you don't need CloudShell: turn the machine on/off from
the AWS Console (EC2 → select the instance → Start / Stop) and use it in any
browser with the address and password.

## Using it from other devices

- **Any computer, tablet or phone browser**: once the machine is on, the
  address and password work from anywhere — buttons not needed.
- **Turning it on/off without the Mac**: install the "AWS Console" app on your
  phone (or aws.amazon.com in any browser), log in, go to EC2, pick the
  instance and choose Start / Stop. Nothing to install on the device.

## How to use it (every time)

There are numbered buttons in this folder. Just double-click them.

**Step 1 — Turn it on.** Double-click **`1 - Turn ON Tally Computer`**.
A black window opens and after about 2 minutes it shows you an address like:

    https://3.111.198.54:8443

**Step 2 — Open that address in your browser** (Chrome or Safari). Type it
exactly as shown. ⚠️ The address **changes every time** you turn the computer
on — always use the one from the black window, not an old bookmark.

Your browser will show a scary warning like *"Your connection is not private"*.
**This is normal and safe** — it appears because this is your own private
computer, not a public website. Click **Advanced → Proceed / Continue**.

**Step 3 — Log in.** Username is `Administrator`. For the password,
double-click **`2 - Get Password`** — it prints the password. (Save it in your
phone's notes the first time; it never changes.)

**Step 4 — Do your work.** Tally is on the desktop. Your GST, Income-tax,
TRACES, EPFO, ESIC and MCA websites are in the **"Govt Portals"** folder on the
desktop. Always keep your Tally company data in the **C:\TallyData** folder.

**Step 5 — Turn it off when done.** Double-click **`5 - Turn OFF Tally Computer`**.
(If you forget — don't worry. The computer switches itself off after about an
hour of sitting idle, and emails you that it did.)

## Signing with your DSC (the USB pen-drive-like token)

Your DSC stays plugged into **your own computer at home** — not the cloud one.
It gets "beamed" to the cloud computer:

- **From a Windows laptop:** connect using the Remote Desktop app instead of
  the browser. Before connecting, in the app's settings turn on
  *Local Resources → Smart cards*. That's it — the portal will see your token.
- **From a Mac:** use the VirtualHere app (one-time setup — ask whoever set
  this system up for you, it takes 10 minutes; the steps are in the "DSC Setup"
  folder on the cloud computer's desktop).
- **Often you don't need the DSC at all:** GST and Income-tax accept an
  **OTP on your Aadhaar-linked mobile** instead, if your firm is a
  proprietorship or partnership. Companies and LLPs must use the DSC.

## Is everything working? (health check)

Two ways, both safe to run any time:

- On your Mac: double-click **`3 - Check Everything OK`**.
- On the cloud computer's desktop: double-click **"Check System Health"**.

Every line says **PASS** (good), **WARN** (fine, just information) or **FAIL**
(a problem — the same line tells you the fix, or show it to whoever manages
this for you).

## If you cannot connect

9 times out of 10 the reason is: your internet company quietly changed your
home connection's address, and the cloud computer only trusts *your* address
(that's a security feature, not a bug).

**The fix is one double-click:** **`4 - Fix Connection Problem`**. Wait for it
to finish, then try Step 1 again.

## Common questions

**What if I press a button twice, or the wrong one?**
Nothing bad happens — ever. All buttons are safe to repeat:
- *Turn ON* when it's already on: it just shows you the address again.
- *Turn OFF* when it's already off: nothing happens.
- *First Time Setup* again: it checks everything, says "already done", and
  stops. It will never create a second cloud computer or bill you twice.
- *Check* and *Get Password*: only look, never change anything.
- *Fix Connection*: just re-saves your current address; running it twice is
  the same as once.

**I forgot to turn it off — will I get a huge bill?**
No. It turns itself off after ~1 hour of inactivity and emails you. There is
also a monthly budget alarm: if spending ever heads past about Rs. 2,000, you
get a warning email long before it becomes a problem.

**I deleted something in Tally by mistake!**
A backup of the whole computer is taken every night at 2 AM (the last 14 nights
are kept). Whoever manages this for you can bring back yesterday's copy.

**Can I use it from my phone or another computer?**
Yes — from anywhere. You only need the address and the password. But the
"turn on / turn off" buttons live on the main Mac. (An administrator can also
start it from the AWS phone app.)

**The Tally screen asks about a license?**
Tally's license was activated once during setup with your serial number. If it
ever asks again, choose "Reactivate" and log in with your Tally.net ID.

## The two rules

1. **Never** log in to the AWS website and delete ("terminate") anything —
   that is the only way to truly lose data, and it is deliberately locked, so
   you'd have to try hard. Just don't.
2. When in doubt, run **`3 - Check Everything OK`** and read what it says.
