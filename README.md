# تطبيق «السالفة بدقيقة» 📱

تطبيق أندرويد (APK) يعرض موقع الصفحة، ويوصل إشعار لكل الناس من تنشر بوست جديد بالانستكرام.
المستودع **خاص (Private)**، يعني انت بس تكدر تعدّل وتطوّر.

---

## 1) ارفع المشروع على GitHub
1. ادخل github.com ← **New repository** ← سمّه `salfa-app` ← اختار **Private** ← Create.
2. اضغط **uploading an existing file** واسحب كل الملفات والمجلدات اللي بالـ ZIP (بعد ما تفكه).
   - مهم: مجلد `.github` لازم يترفع. إذا ما بيّن، فعّل «إظهار الملفات المخفية» بالحاسبة.
3. اضغط **Commit changes**.

بعدها GitHub يبني التطبيق وحده خلال 5 دقايق تقريباً.
تلكاه بصفحة المستودع ← **Releases** ← `salfa-bdaqiqa.apk`. هذا رابط التنزيل اللي تنشره للناس.

> التطبيق يشتغل من هسه، بس الإشعارات تشتغل بعد الخطوة 2 و 3.

---

## 2) شغّل الإشعارات (Firebase، ببلاش)
1. ادخل console.firebase.google.com ← **Add project** ← سمّه `salfa-bdaqiqa`.
2. داخل المشروع اضغط أيقونة **Android** ← بخانة Package name اكتب بالضبط:
   `com.salfa.bdaqiqa` ← Register ← نزّل ملف **google-services.json**.
3. من ⚙️ **Project settings** ← **Service accounts** ← **Generate new private key**، فينزل ملف JSON ثاني.
4. بالمستودع بـ GitHub: **Settings ← Secrets and variables ← Actions ← New repository secret** وسوّي اثنين:
   | الاسم | القيمة |
   |---|---|
   | `GOOGLE_SERVICES_JSON` | كل محتوى ملف google-services.json |
   | `FIREBASE_SERVICE_ACCOUNT` | كل محتوى ملف الـ private key |
5. روح **Actions ← Build APK ← Run workflow** حتى ينبني تطبيق جديد بيه الإشعارات.

**تجربة:** Actions ← **Notify new Instagram posts** ← Run workflow ← اكتب أي رسالة، فتوصل إشعار لكل اللي منزلين التطبيق.

---

## 3) اربط الانستكرام (حتى الإشعار يجي وحده)
1. حوّل حساب salfa.bdaqiqa إلى **Creator** أو **Business** من إعدادات الانستكرام.
2. من developers.facebook.com سوّي App ← أضف **Instagram API with Instagram Login** ← طلّع **Access Token** لحسابك.
3. ضيفه كـ Secret باسم `INSTAGRAM_TOKEN`.

بعدها كل 30 دقيقة يشيّك على حسابك، ومن يلكه نازل بوست جديد يرسل إشعار:
**«سالفة جديدة 🔥»** + أول سطر من الكابشن.

> التوكن ينتهي بعد 60 يوم تقريباً، فلازم تجدده وتحدّث الـ Secret.

---

## تحديث التطبيق
أي تعديل ترفعه على مجلد `android` يبني نسخة جديدة وحده. الناس ينزلونها وتنصب **فوق القديمة** (نفس مفتاح التوقيع).
⚠️ لا تحذف ملف `android/app/salfa-release.jks`، ولا تخلي المستودع Public. إذا ضاع هذا الملف، الناس يضطرون يمسحون التطبيق وينزلونه من جديد.

## ملاحظات
- رابط الموقع اللي يفتحه التطبيق موجود بـ `android/app/build.gradle.kts` (`SITE_URL`).
- روابط الانستكرام والتيك توك داخل الموقع تنفتح بتطبيقاتها.
- عند التنصيب، الموبايل يطلب «السماح بالتثبيت من مصادر غير معروفة». هذا طبيعي لأي تطبيق مو من Google Play.
