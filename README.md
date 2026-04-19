# 📊 סורק מניות אוטומטי — GitHub Actions

סריקת NYSE + NASDAQ שרצה **בענן, בחינם**, כל יום בסגירת השוק בארה"ב, ושולחת לך מייל עם קובץ Excel מצורף.

אין צורך שהמחשב יהיה דלוק. GitHub Actions מריץ עבורך.

---

## 💰 עלות

**חינם לחלוטין** — GitHub נותן 2,000 דקות חודשיות בחינם לחשבונות פרטיים. סריקה יומית צורכת ~15 דקות → כ-300 דקות בחודש. רחוק מהתקרה.

> 💡 אם תהפוך את הריפו ל-**Public** — אין שום מגבלה על דקות. כלומר חינם לנצח.

---

## 🚀 התקנה — 5 צעדים

### שלב 1 — צור חשבון GitHub (אם אין לך)
עבור ל-[github.com](https://github.com) והירשם.

### שלב 2 — צור Gmail App Password
GitHub צריך סיסמה מיוחדת כדי לשלוח דרך ה-Gmail שלך:

1. היכנס ל-[myaccount.google.com/security](https://myaccount.google.com/security)
2. הפעל **2-Step Verification** (אם עדיין לא)
3. עבור ל-[myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
4. בחר App name: "Stock Scanner" → **Create**
5. **העתק את הסיסמה של 16 התווים** (רווחים לא משנים)

### שלב 3 — צור ריפו חדש ודחוף את הקבצים

אופציה A — דרך האתר (קל יותר):
1. ב-GitHub לחץ **New repository** → קרא לו `stock-scanner` → **Private** → **Create**
2. לחץ **uploading an existing file**
3. גרור את כל הקבצים מהתיקייה הזו (`stock_scanner.py`, `requirements.txt`, `.gitignore`, וגם את תיקיית `.github/`)
4. **Commit changes**

אופציה B — דרך הטרמינל:
```bash
cd "~/Documents/Claude/Projects/סורק מניות/github-deploy"
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/stock-scanner.git
git push -u origin main
```

### שלב 4 — הגדר Secrets

בריפו שלך ב-GitHub, עבור ל-**Settings → Secrets and variables → Actions → New repository secret**.

הוסף שלושה secrets:

| Name | Value |
|---|---|
| `SMTP_USER` | כתובת ה-Gmail שלך, לדוגמה `thhk12314@gmail.com` |
| `SMTP_PASSWORD` | ה-App Password בן 16 התווים משלב 2 |
| `MAIL_TO` | הכתובת שתקבל את המייל, לדוגמה `helelit22@gmail.com` |

### שלב 5 — הפעלה ראשונה (ידנית, כדי לבדוק שהכל עובד)

1. בריפו עבור ללשונית **Actions**
2. בחר **Daily Stock Scan** מימין
3. לחץ **Run workflow** → **Run workflow**
4. המתן כ-10-15 דקות ובדוק את המייל שלך

---

## ⏰ מתי זה רץ אוטומטית?

הסריקה רצה **כל יום שני–שישי בשעה 21:30 UTC**, שזה:
- **00:30 בלילה שעון ישראל (קיץ)**
- **23:30 בלילה שעון ישראל (חורף)**

כלומר כ-30 דקות אחרי סגירת השוק בארה"ב (16:00 ET = 20:00/21:00 UTC).

### רוצה לשנות את השעה?
ערוך את הקובץ `.github/workflows/daily-scan.yml` — את השורה:
```yaml
- cron: '30 21 * * 1-5'
```
הפורמט: `minute hour day month day-of-week` (הכול ב-UTC).

דוגמאות:
- `0 22 * * 1-5` → 22:00 UTC כל יום חול
- `0 6 * * *` → 06:00 UTC כל יום (גם סופ"ש)

---

## 📂 איפה קבצי ה-Excel?

1. **במייל** — מצורפים לכל דוח.
2. **ב-GitHub** — בלשונית **Actions**, לחץ על הריצה האחרונה → גלול למטה ל-**Artifacts** → הורד את ה-ZIP.

הקבצים נשמרים 30 יום ב-Artifacts.

---

## 🛠️ פתרון תקלות

**המייל לא מגיע?**
- בדוק שה-App Password נכון (בלי רווחים עובדים טוב יותר)
- ודא שה-SMTP_USER הוא כתובת Gmail (לא Outlook/Yahoo — דורש הגדרות אחרות)
- בדוק תיקיית Spam

**ה-workflow נכשל?**
- בלשונית Actions לחץ על הריצה הכושלת → פתח את הלוגים → חפש את השגיאה
- טעות נפוצה: חסר secret, או סיסמת Gmail שגויה

**רוצה לבטל זמנית?**
- Actions → Daily Stock Scan → **⋯** בימין → **Disable workflow**

---

## 🎯 מה השלב הבא?

אחרי ההתקנה, תוכל:
- לקבל הודעת Push במקום מייל (Pushover/Telegram)
- לשמור היסטוריה ב-Google Sheets
- להוסיף אינדיקטורים נוספים לסריקה

פשוט בקש ממני.
