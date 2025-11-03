# Vehicle Automations

This folder contains automations for vehicle management, specifically for the BMW i4 M50.

## Automations

### BMW Auto Lock

**Alias:** `BMW Auto Lock`
**ID:** `bmw_auto_lock`
**Mode:** `restart`

**Description:**
Automatically locks the BMW i4 M50 when it's at home and has been unlocked for a certain period, with mobile notification. This provides security and peace of mind by ensuring the car doesn't remain unlocked.

**Triggers:**
- `device_tracker.i4_m50` changes to "home" for 10 minutes
- `lock.i4_m50` changes from "locked" to "unlocked" for 30 minutes

**Conditions:**
All conditions must be true:
- `device_tracker.i4_m50` state is "home"
- `lock.i4_m50` state is "unlocked"

**Actions:**
1. Lock the car: `lock.i4_m50`
2. Send notification to Jakub's iPhone:
   - Title: "BMW Auto Lock"
   - Message: "Your BMW i4 M50 has been automatically locked"
   - Category: "car_notification"

**Example Scenarios:**

*Arriving home and forgetting to lock:*
1. You arrive home at 6:00 PM
2. Car is parked in the driveway/garage
3. You forget to lock the car and go inside
4. `device_tracker.i4_m50` registers as "home"
5. After 10 minutes (6:10 PM), car is still unlocked
6. Automation triggers and locks the car
7. You receive notification: "Your BMW i4 M50 has been automatically locked"
8. Peace of mind - car is secure

*Unlocking car at home temporarily:*
1. Car is already at home and locked
2. You unlock it at 3:00 PM to get something from the car
3. You get distracted and forget to lock it again
4. After 30 minutes (3:30 PM), car is still unlocked
5. Automation triggers and locks the car
6. Notification confirms the car has been secured

*Quick use - no auto-lock:*
1. You unlock the car to grab something quickly
2. You lock it again within a few minutes
3. Car never stays unlocked for 30 minutes
4. Automation doesn't trigger
5. No unnecessary locking/notifications

*Away from home:*
1. You're at the grocery store
2. `device_tracker.i4_m50` shows location as not "home"
3. Even if car is unlocked, automation doesn't trigger
4. Auto-lock only works when car is at home
5. Prevents interference with normal away-from-home usage

**Key Features:**
- Two trigger scenarios:
  - 10 minutes after arriving home while unlocked
  - 30 minutes after unlocking while already at home
- Only operates when car is confirmed to be at home
- Both conditions (at home AND unlocked) must be met
- Mobile notification provides confirmation
- Restart mode allows automation to restart if conditions change

**Security Benefits:**
- Prevents car from being left unlocked at home
- Automatic security without manual intervention
- Notification confirms action was taken
- Protects against forgetfulness
- Works whether arriving home or unlocking while at home

**Timing Rationale:**
- **10-minute delay after arrival:** Allows time to unload groceries, bags, etc. before locking
- **30-minute delay after unlocking at home:** Allows time for extended tasks like cleaning, organizing, or maintenance

**Notification Details:**
- Sent to: Jakub's iPhone (`notify.mobile_app_jakub_iphone`)
- Category: `car_notification` (can be used for notification grouping/actions)
- Confirms the automatic action
- Provides peace of mind
