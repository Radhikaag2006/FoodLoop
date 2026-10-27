"use strict";
/* Hindi text for FoodLoop. Keys are the exact English text on screen.
   Words people say every day (pickup, lot, plant) are kept in simple
   Devanagari. Have a native Hindi speaker review before launch. */
Object.assign(I18N.hi, {
  /* ---- tabs and headings ---- */
  "Home": "होम", "Lots": "लॉट", "Add lot": "लॉट जोड़ें", "Records": "रिकॉर्ड", "Account": "खाता",
  "Week": "हफ़्ता", "Pool": "जमा माल", "Runs": "ट्रिप", "Sites": "प्लांट",
  "Overview": "सारांश", "Verify": "जाँचें", "People": "लोग", "Main": "मुख्य",
  "My week": "मेरा हफ़्ता", "Facilities": "प्लांट", "Notifications": "सूचनाएँ", "Back": "वापस", "Next": "आगे",
  "Skip": "छोड़ें", "Continue": "आगे बढ़ें", "Save": "सहेजें", "Cancel": "रद्द करें", "Confirm": "पक्का करें",
  "OK": "ठीक है", "Delete": "हटाएँ", "Remove": "हटाएँ", "View": "देखें", "Upload": "अपलोड करें", "Share": "शेयर करें",
  "Check": "जाँचें", "Choose": "चुनें", "Change": "बदलें", "Pay": "भुगतान करें", "Call": "फ़ोन करें",
  "Copied": "कॉपी हो गया", "Copy this:": "इसे कॉपी करें:", "Try again": "फिर कोशिश करें",
  "Couldn't load this": "यह लोड नहीं हो सका", "Nothing here": "यहाँ कुछ नहीं है",
  "Something went wrong.": "कुछ गड़बड़ हो गई।", "Something went wrong. Please try again.": "कुछ गड़बड़ हो गई। कृपया फिर कोशिश करें।",
  "No connection. Check your internet and try again.": "इंटरनेट नहीं है। इंटरनेट देखकर फिर कोशिश करें।",
  "Escape": "बंद करें", "Name": "नाम", "Phone": "फ़ोन", "Address": "पता", "Status": "स्थिति", "Type": "प्रकार",
  "Today": "आज", "Yesterday": "कल", "just now": "अभी-अभी", "Good morning": "सुप्रभात", "Good afternoon": "नमस्कार", "Good evening": "शुभ संध्या",
  "All": "सभी", "Done": "पूरा", "Waiting": "इंतज़ार में", "Planned": "तय हुआ", "Collected": "उठा लिया", "Closed": "पूरा हुआ",
  "Accepted": "स्वीकार", "Rejected": "अस्वीकार", "Cancelled": "रद्द", "Requested": "माँगा गया", "Handed over": "सौंप दिया", "Turned off": "बंद",
  "Retired": "बंद किया गया", "Active": "चालू", "Off": "बंद", "On": "चालू", "Free": "मुफ़्त", "Paid": "चुकाया", "Due": "बाकी", "To pay": "चुकाना है",
  "Later": "बाद में", "To": "को", "Enter": "डालें", "Pass": "छोड़ें", "Open run": "ट्रिप खोलें", "Mode:": "मोड:",

  /* ---- welcome, sign in, sign up ---- */
  "Dispose of surplus food safely.": "बचा हुआ खाना सुरक्षित तरीक़े से हटाएँ।",
  "Add your expired stock. We plan the pickup and give you a record you can show auditors.": "अपना एक्सपायर्ड माल जोड़ें। पिकअप हम तय करेंगे और आपको ऑडिट में दिखाने लायक़ रिकॉर्ड देंगे।",
  "Expired stock has somewhere to go.": "एक्सपायर्ड माल के लिए सही जगह है।",
  "Add expired or surplus food as a lot. FoodLoop picks the right route and the best nearby facility.": "एक्सपायर्ड या बचा खाना एक “लॉट” के रूप में जोड़ें। FoodLoop सही रास्ता और पास का सबसे अच्छा प्लांट चुनता है।",
  "We plan the pickup.": "पिकअप हम तय करते हैं।",
  "A collector plans a run once enough lots are waiting, weighs the load, and hands it to a certified facility.": "जब काफ़ी लॉट जमा हो जाते हैं, कलेक्टर ट्रिप बनाता है, माल तौलता है और उसे प्रमाणित प्लांट को सौंप देता है।",
  "Expired food never reaches a plate.": "एक्सपायर्ड खाना कभी थाली तक नहीं पहुँचता।",
  "FoodLoop checks expiry dates and sends expired food only to certified compost or biogas, with a record anyone can verify.": "FoodLoop एक्सपायरी की तारीख़ जाँचता है और एक्सपायर्ड खाना सिर्फ़ प्रमाणित कंपोस्ट या बायोगैस प्लांट में भेजता है। इसका रिकॉर्ड कोई भी जाँच सकता है।",
  "Get started": "शुरू करें", "Create account": "खाता बनाएँ", "Sign in": "लॉग इन करें",
  "Have a FoodLoop record code?": "क्या आपके पास FoodLoop रिकॉर्ड कोड है?", "Check a disposal record": "निपटान रिकॉर्ड जाँचें",
  "Welcome back": "फिर स्वागत है", "Welcome to FoodLoop": "FoodLoop में आपका स्वागत है",
  "Sign in with your mobile number or email.": "अपने मोबाइल नंबर या ईमेल से लॉग इन करें।",
  "Mobile number or email": "मोबाइल नंबर या ईमेल", "Password": "पासवर्ड", "Show password": "पासवर्ड दिखाएँ", "Forgot password?": "पासवर्ड भूल गए?",
  "Try a demo account": "डेमो खाता आज़माएँ", "Demo accounts": "डेमो खाते", "Fictional data for trying the app. Password for all:": "ऐप आज़माने के लिए नक़ली डेटा। सभी का पासवर्ड:",
  "New here?": "नए हैं?", "Create an account": "खाता बनाएँ", "Create your account": "अपना खाता बनाएँ",
  "How will you use FoodLoop?": "आप FoodLoop कैसे इस्तेमाल करेंगे?",
  "I run a food business": "मेरा खाने का कारोबार है", "Distributor, manufacturer, retailer or caterer with expired or surplus stock": "डिस्ट्रीब्यूटर, निर्माता, दुकानदार या कैटरर, जिनके पास एक्सपायर्ड या बचा माल है",
  "Pickup staff invited by FoodLoop": "FoodLoop द्वारा बुलाया गया पिकअप स्टाफ़", "I have an invite code": "मेरे पास इन्वाइट कोड है",
  "Already have an account?": "पहले से खाता है?", "City": "शहर", "Choose your city": "अपना शहर चुनें", "Use my exact location": "मेरी सटीक लोकेशन इस्तेमाल करें",
  "Business name": "कारोबार का नाम", "Business type": "कारोबार का प्रकार", "FSSAI licence number": "FSSAI लाइसेंस नंबर",
  "Needed to verify your business. You can add it later.": "आपके कारोबार की जाँच के लिए ज़रूरी है। बाद में भी डाल सकते हैं।",
  "Distributor or wholesaler": "डिस्ट्रीब्यूटर या थोक व्यापारी", "Manufacturer or packer": "निर्माता या पैकर", "Retailer or supermarket": "दुकानदार या सुपरमार्केट",
  "Restaurant or caterer": "रेस्टोरेंट या कैटरर", "Other": "अन्य", "Register your business": "अपना कारोबार दर्ज करें",
  "We verify your details before pickups start.": "पिकअप शुरू होने से पहले हम आपकी जानकारी जाँचते हैं।",
  "Join with an invite": "इन्वाइट से जुड़ें", "Enter the code your organisation sent you.": "आपकी संस्था ने जो कोड भेजा है, वह डालें।",
  "Invite accepted": "इन्वाइट स्वीकार हुआ", "Your name": "आपका नाम", "Full name": "पूरा नाम", "Mobile number": "मोबाइल नंबर", "Mobile": "मोबाइल",
  "Email": "ईमेल", "(optional)": "(ज़रूरी नहीं)", "Lets you reset your password by email.": "इससे आप ईमेल द्वारा पासवर्ड बदल सकते हैं।",
  "I agree to the": "मैं सहमत हूँ:", "Terms and Privacy notice": "शर्तें और प्राइवेसी सूचना",
  "Create a password": "पासवर्ड बनाएँ", "At least 8 characters with a letter and a number.": "कम से कम 8 अक्षर, जिसमें एक अक्षर और एक संख्या हो।",
  "Reset your password": "पासवर्ड बदलें",
  "Enter your mobile number or email. If you added an email, we'll send a 6-digit code. Otherwise ask the FoodLoop team for a code.": "अपना मोबाइल नंबर या ईमेल डालें। अगर आपने ईमेल जोड़ा है तो हम 6 अंकों का कोड भेजेंगे। नहीं तो FoodLoop टीम से कोड माँगें।",
  "Send code": "कोड भेजें", "I already have a code": "मेरे पास कोड है", "Enter your code": "अपना कोड डालें",
  "Use the 6-digit code for": "इसके लिए 6 अंकों का कोड इस्तेमाल करें:", ", then choose a new password.": ", फिर नया पासवर्ड चुनें।",
  "Development mode": "डेवलपमेंट मोड", "Your code is {}. This is never shown in production.": "आपका कोड {} है। यह असली ऐप में नहीं दिखता।",
  "6-digit code": "6 अंकों का कोड", "Set new password": "नया पासवर्ड रखें", "New password": "नया पासवर्ड",
  "Password updated. Sign in with it.": "पासवर्ड बदल गया। इससे लॉग इन करें।",
  "Location isn't available on this device.": "इस फ़ोन में लोकेशन उपलब्ध नहीं है।", "Getting location…": "लोकेशन ली जा रही है…", "Location saved.": "लोकेशन सहेज ली गई।",
  "Couldn't get location. Choose your city instead.": "लोकेशन नहीं मिली। अपना शहर चुनें।", "Please agree to the Terms and Privacy notice.": "कृपया शर्तें और प्राइवेसी सूचना मानें।",
  "Waste less. Earn more.": "कचरा कम, कमाई ज़्यादा।", "Admin": "एडमिन", "FoodLoop admin": "FoodLoop एडमिन",
  "8-character code": "8 अक्षर का कोड", "14 digits": "14 अंक", "Street, area": "गली, इलाक़ा", "e.g. Fresh Foods Pvt Ltd": "जैसे: फ्रेश फूड्स प्रा. लि.",
  "Waiting for approval": "मंज़ूरी का इंतज़ार",

  /* ---- business home, lots ---- */
  "Add a lot": "लॉट जोड़ें", "Add lot": "लॉट जोड़ें", "Your lots": "आपके लॉट", "Recent pickups": "हाल के पिकअप", "No pickups yet": "अभी कोई पिकअप नहीं",
  "Add your expired or surplus stock. We'll match it to a certified facility and plan the pickup.": "अपना एक्सपायर्ड या बचा माल जोड़ें। हम उसे प्रमाणित प्लांट से जोड़कर पिकअप तय करेंगे।",
  "Waiting by route": "रास्ते के हिसाब से इंतज़ार में", "No lots here": "यहाँ कोई लॉट नहीं", "Add expired or surplus stock and we'll plan the pickup.": "एक्सपायर्ड या बचा माल जोड़ें, पिकअप हम तय करेंगे।",
  "What is it?": "यह क्या है?", "Condition": "हालत", "Quantity (kg)": "मात्रा (kg)", "Quantity": "मात्रा", "Expiry date": "एक्सपायरी की तारीख़", "Expiry": "एक्सपायरी",
  "Date printed on pack.": "पैक पर छपी तारीख़।", "Lot added": "लॉट जुड़ गया", "Add another": "एक और जोड़ें", "View lots": "लॉट देखें",
  "Fresh food is only collected if it has passed its expiry date.": "ताज़ा खाना तभी लिया जाता है जब उसकी एक्सपायरी की तारीख़ निकल चुकी हो।",
  "Fresh": "ताज़ा", "Overripe": "ज़्यादा पका", "Bruised": "चोट खाया / दबा हुआ", "Spoiled": "सड़ा हुआ", "Added": "जोड़ा गया", "Route": "रास्ता",
  "Lot": "लॉट", "(expires today)": "(आज एक्सपायर)", "Remove lot": "लॉट हटाएँ", "Remove this lot": "यह लॉट हटाएँ", "Remove this lot?": "यह लॉट हटाएँ?",
  "It won't be included in any pickup.": "यह किसी पिकअप में शामिल नहीं होगा।", "Lot removed": "लॉट हटा दिया गया",
  "Vegetables": "सब्ज़ियाँ", "Fruits": "फल", "Dairy": "डेयरी", "Bakery and bread": "बेकरी और ब्रेड", "Grains, flour and pulses": "अनाज, आटा और दालें",
  "Packaged snacks and biscuits": "पैकेट वाले स्नैक्स और बिस्कुट", "Cooked and ready-to-eat food": "पका हुआ और खाने को तैयार खाना",
  "Mixed kitchen waste": "मिला-जुला रसोई का कचरा", "Empty packaging": "ख़ाली पैकेजिंग",
  "Process": "प्रोसेस", "Feed": "चारा", "Recover": "रिकवर", "Packaging": "पैकेजिंग",
  "Pulp, jam, pickle, dehydration units": "पल्प, जैम, अचार, सुखाने वाली इकाइयाँ", "Animal feed makers (non-expired surplus only)": "पशु चारा बनाने वाले (सिर्फ़ बिना एक्सपायर बचा माल)",
  "Certified compost or anaerobic digestion": "प्रमाणित कंपोस्ट या बायोगैस प्लांट", "Packaging recycling": "पैकेजिंग रीसाइक्लिंग",
  "Fixed route for this item type.": "इस तरह के माल का रास्ता तय है।",
  "Expired: human-food, process and feed routes are locked. Certified compost or digestion only.": "एक्सपायर्ड: इंसानी खाने, प्रोसेस और चारे के रास्ते बंद हैं। सिर्फ़ प्रमाणित कंपोस्ट या बायोगैस।",
  "Spoiled: only certified compost or digestion.": "सड़ा हुआ: सिर्फ़ प्रमाणित कंपोस्ट या बायोगैस।",
  "Not fit for people but safe: feed route.": "इंसानों के खाने लायक़ नहीं, पर सुरक्षित: चारे का रास्ता।",
  "Damaged and not feed-suitable: certified compost.": "ख़राब और चारे लायक़ नहीं: प्रमाणित कंपोस्ट।",
  "Overripe but usable: processing units.": "ज़्यादा पका पर काम का: प्रोसेसिंग इकाई।",
  "No eligible plant is listed for this route yet. We'll tell you when one is added.": "इस रास्ते के लिए अभी कोई प्लांट सूची में नहीं है। जुड़ते ही हम बताएँगे।",
  "Waiting for your business to be verified": "आपके कारोबार की जाँच का इंतज़ार", "Waiting for a pickup": "पिकअप का इंतज़ार",
  "Pickups are only planned once an admin has verified your business.": "एडमिन के आपके कारोबार को जाँचने के बाद ही पिकअप तय होते हैं।",
  "A collector plans a run once enough lots are waiting for the same facility. You'll get a notification when it's planned.": "जब एक ही प्लांट के लिए काफ़ी लॉट जमा हो जाते हैं, कलेक्टर ट्रिप बनाता है। तय होते ही आपको सूचना मिलेगी।",
  "Verification in progress": "जाँच चल रही है", "Add your FSSAI licence number in Account so we can verify you. You can add lots meanwhile.": "हम जाँच सकें इसके लिए खाते में FSSAI लाइसेंस नंबर डालें। तब तक आप लॉट जोड़ सकते हैं।",
  "Verification declined": "जाँच अस्वीकार", "Please contact FoodLoop support to fix your details.": "जानकारी सुधारने के लिए कृपया FoodLoop सपोर्ट से संपर्क करें।",
  "Add your FSSAI licence number": "अपना FSSAI लाइसेंस नंबर डालें",
  "FSSAI": "FSSAI", "FSSAI licence": "FSSAI लाइसेंस", "Not given": "नहीं दिया",
  "Tip: FoodLoop is a waste disposal platform. If this is food waste, select": "सुझाव: FoodLoop कचरा निपटान का प्लेटफ़ॉर्म है। अगर यह खाने का कचरा है, तो चुनें:",
  "(pulp/pickling),": "(पल्प/अचार),", "(animal feed), or": "(पशु चारा), या", "(compost/biogas). Fresh food is only accepted if it has already passed its expiry date.": "(कंपोस्ट/बायोगैस)। ताज़ा खाना तभी लिया जाता है जब उसकी एक्सपायरी निकल चुकी हो।",
  "Use it to see where your waste goes.": "इससे देखें कि आपका कचरा कहाँ गया।", "Lot added": "लॉट जुड़ गया",
  "This food is still in date and in good condition, so it isn't waste. FoodLoop only collects expired, spoiled or damaged food.": "यह खाना अभी एक्सपायर नहीं हुआ और अच्छी हालत में है, इसलिए यह कचरा नहीं है। FoodLoop सिर्फ़ एक्सपायर्ड, सड़ा या ख़राब खाना लेता है।",

  /* ---- pickup details and tracking ---- */
  "Pickup details": "पिकअप की जानकारी", "Tracking": "ट्रैकिंग", "Tracking ID": "ट्रैकिंग आईडी", "Track this order": "इस ऑर्डर को ट्रैक करें",
  "Track": "ट्रैक", "Scan the QR": "QR स्कैन करें", "Type the ID instead": "इसकी जगह आईडी लिखें", "Scan QR code": "QR कोड स्कैन करें",
  "Point your camera at the QR code on your order. If the camera doesn't work, type the ID instead.": "अपने ऑर्डर के QR कोड पर कैमरा रखें। कैमरा न चले तो आईडी लिखें।",
  "Track your waste": "अपना कचरा ट्रैक करें", "Enter a tracking ID or scan the QR to see where it went.": "यह देखने के लिए कि वह कहाँ गया, ट्रैकिंग आईडी डालें या QR स्कैन करें।",
  "Enter the tracking ID from your order.": "अपने ऑर्डर की ट्रैकिंग आईडी डालें।",
  "The camera needs a secure (https) connection. Type the ID instead.": "कैमरे के लिए सुरक्षित (https) कनेक्शन चाहिए। आईडी लिखें।",
  "Couldn't open the camera. Type the ID instead.": "कैमरा नहीं खुला। आईडी लिखें।", "Track an order": "ऑर्डर ट्रैक करें", "Where is my waste?": "मेरा कचरा कहाँ है?",
  "Type the tracking ID from your order, or scan its QR code.": "अपने ऑर्डर की ट्रैकिंग आईडी लिखें या उसका QR कोड स्कैन करें।",
  "Your orders": "आपके ऑर्डर", "Order tracking": "ऑर्डर ट्रैकिंग", "Track another order": "दूसरा ऑर्डर ट्रैक करें",
  "Check the ID and try again.": "आईडी जाँचकर फिर कोशिश करें।", "No order found": "कोई ऑर्डर नहीं मिला", "Copy tracking link": "ट्रैकिंग लिंक कॉपी करें",
  "Copy tracking ID": "ट्रैकिंग आईडी कॉपी करें", "Tracking QR code": "ट्रैकिंग QR कोड", "Journey": "सफ़र", "Where it went": "कहाँ गया", "How it was used": "कैसे इस्तेमाल हुआ",
  "Confirmed weight": "पक्का वज़न", "Type an ID or scan a QR.": "आईडी लिखें या QR स्कैन करें।", "Matched": "मेल खाया", "Flagged": "निशान लगा",
  "Order placed": "ऑर्डर दिया गया", "Pickup planned": "पिकअप तय हुआ", "Pickup scheduled": "पिकअप का समय तय हुआ", "On the way to the plant": "प्लांट के रास्ते में",
  "Delivered and processed": "पहुँचा और निपटाया गया",
  "Turned into compost that enriches soil.": "कंपोस्ट बना, जो मिट्टी को उपजाऊ बनाता है।", "Digested to make biogas and bio-fertiliser.": "बायोगैस और जैविक खाद बनाने में इस्तेमाल हुआ।",
  "Processed into products such as pulp, pickle or dehydrated food.": "पल्प, अचार या सुखाए गए खाने जैसे उत्पादों में बदला गया।", "Used as animal feed.": "पशु चारे के रूप में इस्तेमाल हुआ।", "Sent for recycling.": "रीसाइक्लिंग के लिए भेजा गया।",
  "Pickup number": "पिकअप नंबर", "Collected from": "यहाँ से उठाया", "Your load": "आपका माल", "Whole run (all stops)": "पूरी ट्रिप (सभी स्टॉप)",
  "Hub scale": "हब का तराज़ू", "Facility scale": "प्लांट का तराज़ू", "Weight check": "वज़न की जाँच", "Mismatch flagged": "अंतर दिखा", "Within 5%": "5% के अंदर",
  "Weight mismatch": "वज़न में अंतर", "Hub and facility weights differ by more than 5%.": "हब और प्लांट के वज़न में 5% से ज़्यादा अंतर है।",
  "Your lots in this run": "इस ट्रिप में आपके लॉट", "Where it goes": "यह कहाँ जाएगा", "Where it will go": "यह कहाँ जाएगा", "This pickup": "यह पिकअप",
  "Pickup planned": "पिकअप तय हुआ", "A collector has grouped your lots into a run.": "कलेक्टर ने आपके लॉट एक ट्रिप में जोड़ दिए हैं।",
  "Collected from you": "आपसे उठाया गया", "The collector picks the load up from your address.": "कलेक्टर आपके पते से माल उठाता है।",
  "Weighed and disposed": "तौला और निपटाया गया", "Weighed at the hub and the facility, then a record is issued.": "हब और प्लांट पर तौला जाता है, फिर रिकॉर्ड जारी होता है।",
  "This is a certified facility.": "यह प्रमाणित प्लांट है।", "Your load has been collected and is on its way to be weighed and disposed.": "आपका माल उठा लिया गया है और तौलने व निपटाने के लिए जा रहा है।",
  "A collector will pick this up from your address.": "कलेक्टर इसे आपके पते से उठाएगा।",
  "Waiting for a collector": "कलेक्टर का इंतज़ार", "A collector will confirm the pickup time. You'll get a notification, and their name and number will show here.": "कलेक्टर पिकअप का समय पक्का करेगा। आपको सूचना मिलेगी और उनका नाम व नंबर यहाँ दिखेगा।",
  "Pickup time": "पिकअप का समय", "To be confirmed by the collector": "कलेक्टर पक्का करेगा", "Collector": "कलेक्टर", "Collection": "उठान",
  "Open in Maps": "मैप में खोलें", "Call collector": "कलेक्टर को फ़ोन करें", "Certificate": "प्रमाणपत्र", "Not certified": "प्रमाणित नहीं", "Certified": "प्रमाणित",
  "View certificate document": "प्रमाणपत्र देखें", "Plant": "प्लांट", "Certificate no.": "प्रमाणपत्र नं.", "Document not uploaded yet": "दस्तावेज़ अभी अपलोड नहीं हुआ",
  "The certificate number above is on file. Contact FoodLoop support if you need a copy.": "ऊपर दिया प्रमाणपत्र नंबर रिकॉर्ड में है। कॉपी चाहिए तो FoodLoop सपोर्ट से संपर्क करें।",
  "Address on request": "पता माँगने पर", "Disposed at": "यहाँ निपटाया", "CO₂e avoided*": "बचा CO₂e*",
  "*Placeholder factor, not an audited figure.": "*अनुमानित आँकड़ा, जाँचा हुआ नहीं।", "placeholder factor, not an audited figure": "अनुमानित आँकड़ा, जाँचा हुआ नहीं",
  "waiting for pickup": "पिकअप के इंतज़ार में", "safely disposed": "सुरक्षित निपटाया", "pickups on the way": "पिकअप रास्ते में", "kg collected": "kg उठाया",

  /* ---- records, verify ---- */
  "All records": "सभी रिकॉर्ड", "No records yet": "अभी कोई रिकॉर्ड नहीं", "Records appear here after a pickup is collected, weighed and closed.": "पिकअप उठने, तुलने और पूरा होने के बाद रिकॉर्ड यहाँ दिखते हैं।",
  "Each finished pickup gets a tamper-evident record with a QR code. Share it with auditors or your own customers.": "हर पूरे पिकअप का एक छेड़छाड़-रोधी रिकॉर्ड QR कोड के साथ मिलता है। इसे ऑडिटर या अपने ग्राहकों को दिखाएँ।",
  "Export CSV report": "CSV रिपोर्ट निकालें", "Open PDF": "PDF खोलें", "PDF": "PDF",
  "Enter the code printed on a FoodLoop disposal record, or scan its QR code. Every record is linked to the one before it, so changing any record breaks the check.": "FoodLoop निपटान रिकॉर्ड पर छपा कोड डालें या उसका QR स्कैन करें। हर रिकॉर्ड पिछले से जुड़ा होता है, इसलिए किसी में बदलाव करने पर जाँच टूट जाती है।",
  "This confirms the record hasn't been changed after it was issued. It isn't an official FSSAI or pollution board certificate.": "यह पक्का करता है कि रिकॉर्ड जारी होने के बाद बदला नहीं गया। यह FSSAI या प्रदूषण बोर्ड का सरकारी प्रमाणपत्र नहीं है।",
  "Check a record": "रिकॉर्ड जाँचें", "Record is intact": "रिकॉर्ड सही है", "Record doesn't match": "रिकॉर्ड मेल नहीं खाता", "Hash check": "हैश जाँच", "Link to previous record": "पिछले रिकॉर्ड से जुड़ाव",
  "Matches": "मेल खाता है", "Does not match": "मेल नहीं खाता", "Intact": "सही", "Broken": "टूटा", "Facility": "प्लांट", "No record found": "कोई रिकॉर्ड नहीं मिला",
  "Weights (expected / hub / facility)": "वज़न (अपेक्षित / हब / प्लांट)", "Check the code and try again.": "कोड जाँचकर फिर कोशिश करें।",

  /* ---- account ---- */
  "Edit profile": "प्रोफ़ाइल बदलें", "Change password": "पासवर्ड बदलें", "Install FoodLoop on this device": "इस फ़ोन पर FoodLoop इंस्टॉल करें",
  "Terms and privacy": "शर्तें और प्राइवेसी", "Sign out": "लॉग आउट", "Delete my account": "मेरा खाता हटाएँ", "FoodLoop 1.0": "FoodLoop 1.0",
  "You'll stay signed in here. Other devices are signed out.": "आप यहाँ लॉग इन रहेंगे। दूसरे फ़ोन से लॉग आउट हो जाएगा।", "Update password": "पासवर्ड अपडेट करें",
  "Delete your account?": "अपना खाता हटाएँ?", "This signs you out everywhere and removes your name, phone and email. Your lots and disposal records stay, without your personal details. This can't be undone.": "इससे आप हर जगह से लॉग आउट हो जाएँगे और आपका नाम, फ़ोन व ईमेल हट जाएँगे। आपके लॉट और रिकॉर्ड बिना निजी जानकारी के रहेंगे। इसे वापस नहीं किया जा सकता।",
  "Keep account": "खाता रखें", "Profile saved": "प्रोफ़ाइल सहेजी गई", "Current password": "मौजूदा पासवर्ड", "Password updated": "पासवर्ड बदल गया", "Your password": "आपका पासवर्ड", "Account deleted": "खाता हटा दिया गया",
  "You're all caught up": "सब देख लिया", "Updates about your lots, pickups and records will show up here.": "आपके लॉट, पिकअप और रिकॉर्ड की जानकारी यहाँ दिखेगी।",
  "Business details": "कारोबार की जानकारी", "Changing this sends your business for re-verification.": "इसे बदलने पर आपके कारोबार की दोबारा जाँच होगी।", "Contact mobile": "संपर्क मोबाइल",
  "Free trial, plans and invoices": "मुफ़्त ट्रायल, प्लान और बिल", "Plan and billing": "प्लान और बिल", "Draft text": "ड्राफ़्ट पाठ",
  "Have a lawyer review and replace this before you open the app to the public.": "ऐप सबके लिए खोलने से पहले इसे वकील से जँचवाकर बदलें।", "What we collect": "हम क्या लेते हैं", "Why": "क्यों",
  "Your name, mobile number, optional email, your business details (name, address, location, FSSAI number), and the lots you enter (item, weight, expiry).": "आपका नाम, मोबाइल नंबर, वैकल्पिक ईमेल, कारोबार की जानकारी (नाम, पता, लोकेशन, FSSAI नंबर) और आपके डाले लॉट (माल, वज़न, एक्सपायरी)।",
  "To plan pickups, match your lots to facilities and issue disposal records. We don't sell your data.": "पिकअप तय करने, लॉट को प्लांट से जोड़ने और निपटान रिकॉर्ड देने के लिए। हम आपका डेटा बेचते नहीं हैं।",
  "Who can see it": "कौन देख सकता है", "Collectors see pickup totals and stops. FoodLoop admins can see accounts to verify businesses and keep the service safe. Disposal records show organisation names.": "कलेक्टर पिकअप का कुल माल और स्टॉप देखते हैं। FoodLoop एडमिन कारोबार जाँचने और सेवा सुरक्षित रखने के लिए खाते देख सकते हैं। निपटान रिकॉर्ड में संस्था के नाम दिखते हैं।",
  "Your choices": "आपके विकल्प", "You can edit your details or delete your account from Account. Deleting removes your name, phone and email. Past disposal records stay, without your personal details.": "आप खाते में जाकर जानकारी बदल या खाता हटा सकते हैं। हटाने पर नाम, फ़ोन और ईमेल हट जाते हैं। पुराने रिकॉर्ड बिना निजी जानकारी के रहते हैं।",

  /* ---- collector: pool, runs, week ---- */
  "kg waiting": "kg जमा", "Smallest run worth sending": "भेजने लायक़ सबसे छोटी ट्रिप", "kg per facility": "kg प्रति प्लांट",
  "Small groups are clubbed into a nearby run. They only wait here when no run is close enough.": "छोटे लॉट पास की ट्रिप में जोड़ दिए जाते हैं। पास में कोई ट्रिप न हो तभी वे यहाँ रुकते हैं।",
  "Plan pickup runs": "पिकअप ट्रिप बनाएँ", "Still too small:": "अभी भी बहुत छोटे:", "Where it's from": "यह कहाँ से आया", "Business": "कारोबार", "Verified": "जाँचा हुआ", "Not verified": "जाँच नहीं हुई",
  "The pool is empty": "जमा माल ख़ाली है", "Business lots show up here as they come in.": "कारोबारियों के लॉट आते ही यहाँ दिखते हैं।", "It stays in the pool and is skipped when planning runs.": "यह जमा माल में रहता है और ट्रिप बनाते समय छोड़ दिया जाता है।",
  "No runs yet": "अभी कोई ट्रिप नहीं", "See runs": "ट्रिप देखें", "Waiting for the next dispatch batch": "अगले बैच का इंतज़ार", "No collector fits, open to all": "कोई कलेक्टर फ़िट नहीं, सबके लिए खुला",
  "Address not listed": "पता दर्ज नहीं", "Navigate to drop-off": "ड्रॉप-ऑफ़ तक रास्ता देखें", "Call drop-off": "ड्रॉप-ऑफ़ पर फ़ोन करें", "Drop-off": "यहाँ माल छोड़ना है", "Drop-off point": "ड्रॉप-ऑफ़ की जगह",
  "Time not set": "समय तय नहीं", "New runs for you": "आपके लिए नई ट्रिप", "Your week": "आपका हफ़्ता", "No runs": "कोई ट्रिप नहीं", "Nothing booked yet": "अभी कुछ बुक नहीं",
  "New runs show up here with the pay and distance, and you choose which to accept.": "नई ट्रिप कमाई और दूरी के साथ यहाँ दिखती हैं। कौन-सी लेनी है, आप चुनते हैं।",
  "Added to your week": "आपके हफ़्ते में जुड़ गई", "Pass on this run?": "यह ट्रिप छोड़ दें?", "It goes to the next nearest collector.": "यह अगले सबसे पास के कलेक्टर को जाएगी।", "Passed": "छोड़ दी",
  "booked this week": "इस हफ़्ते बुक", "Accepted, time not set": "स्वीकार की, समय तय नहीं", "Set pickup time": "पिकअप का समय तय करें", "Change pickup time": "पिकअप का समय बदलें",
  "Take this run and set time": "यह ट्रिप लें और समय तय करें", "Driver fare": "ड्राइवर का भाड़ा", "Driver fare for this trip": "इस ट्रिप का ड्राइवर भाड़ा",
  "Assigned to you": "आपको दी गई", "Open: no collector fits yet": "खुली: अभी कोई कलेक्टर फ़िट नहीं", "No pickup time set yet. Businesses are waiting to hear from you.": "पिकअप का समय अभी तय नहीं। कारोबारी आपके जवाब का इंतज़ार कर रहे हैं।",
  "Businesses on this run get a notification with the time, your name and your number. Times are India time.": "इस ट्रिप के कारोबारियों को समय, आपके नाम और नंबर की सूचना मिलती है। समय भारतीय समय है।",
  "Arrive from": "पहुँचने का समय (से)", "They are told to expect you within 2 hours of this time.": "उन्हें बताया जाता है कि आप इस समय से 2 घंटे के अंदर आएँगे।", "Confirm time": "समय पक्का करें",
  "Time sent to businesses": "समय कारोबारियों को भेज दिया गया", "Pick a date and time.": "तारीख़ और समय चुनें।", "To do": "करने हैं", "Finished": "पूरी हुईं",
  "Hub / facility": "हब / प्लांट", "Mismatch": "अंतर", "Merchant bills": "कारोबारियों के बिल", "Can't do this run": "यह ट्रिप नहीं कर सकता", "Mark as collected": "उठा लिया, ऐसा लिखें",
  "Weigh and close": "तौलें और पूरा करें", "Hub weight (kg)": "हब का वज़न (kg)", "Facility weight (kg)": "प्लांट का वज़न (kg)", "Close and issue record": "पूरा करें और रिकॉर्ड जारी करें",
  "Weights differ by more than 5%": "वज़न में 5% से ज़्यादा अंतर", "You can still close it. The record will show a mismatch flag.": "आप फिर भी पूरा कर सकते हैं। रिकॉर्ड में अंतर का निशान दिखेगा।",
  "No runs to do": "करने के लिए कोई ट्रिप नहीं", "Nothing finished yet": "अभी कुछ पूरा नहीं हुआ", "Plan runs from the Pool tab when enough waste has built up.": "काफ़ी माल जमा होने पर “जमा माल” टैब से ट्रिप बनाएँ।",
  "Closed runs and their records show up here.": "पूरी हुई ट्रिप और उनके रिकॉर्ड यहाँ दिखते हैं।", "Hand this run back?": "यह ट्रिप वापस करें?", "It goes to the next nearest collector. Any time you set is cancelled.": "यह अगले सबसे पास के कलेक्टर को जाएगी। आपका तय किया समय रद्द हो जाएगा।",
  "Hand back": "वापस करें", "Handed back": "वापस कर दी", "Marked as collected": "उठा लिया, दर्ज हुआ", "Vehicle and start point": "गाड़ी और शुरुआत की जगह",
  "We offer you the runs closest to where your vehicle starts, and only ones it can carry.": "हम आपको वही ट्रिप देते हैं जो आपकी गाड़ी की शुरुआत की जगह के पास हों और जिन्हें आपकी गाड़ी ले जा सके।",
  "Vehicle": "गाड़ी", "Can carry (kg)": "कितना ले जा सकती है (kg)", "Starts from": "यहाँ से शुरू", "Choose a city": "शहर चुनें", "Use my current location": "मेरी मौजूदा लोकेशन इस्तेमाल करें",
  "Available for runs": "ट्रिप के लिए उपलब्ध", "Turn off when you are not working": "काम न कर रहे हों तो बंद कर दें", "Decides which runs you are offered": "तय करता है कि आपको कौन-सी ट्रिप मिलेंगी",
  "Vehicle and start point": "गाड़ी और शुरुआत की जगह", "e.g. Tata Ace": "जैसे: टाटा एस", "my location": "मेरी लोकेशन", "My location": "मेरी लोकेशन", "Or use your current location.": "या अपनी मौजूदा लोकेशन इस्तेमाल करें।",
  "Location isn't available here. Choose a city.": "यहाँ लोकेशन उपलब्ध नहीं। शहर चुनें।", "Couldn't get location. Choose a city instead.": "लोकेशन नहीं मिली। शहर चुनें।", "Choose where your vehicle starts from.": "चुनें कि आपकी गाड़ी कहाँ से शुरू होती है।",
  "Merchant bills": "कारोबारियों के बिल", "What each business pays for this run. Unpaid bills have a UPI QR the merchant can scan.": "इस ट्रिप के लिए हर कारोबारी कितना देता है। बाकी बिलों पर UPI QR है जिसे कारोबारी स्कैन कर सकता है।",
  "Show UPI QR": "UPI QR दिखाएँ", "No bills for this run": "इस ट्रिप के कोई बिल नहीं", "A run's bills appear once it's closed and the business has used its free pickups.": "ट्रिप पूरी होने और कारोबारी के मुफ़्त पिकअप ख़त्म होने के बाद बिल दिखते हैं।",
  "Closed runs": "पूरी हुई ट्रिप", "Route": "रास्ता", "Pick up:": "यहाँ से उठाना है:", "Accept ·": "स्वीकारें ·",
  "Dispatch": "डिस्पैच", "Why:": "वजह:", "open to all": "सबके लिए खुला", "Give out waiting runs now": "इंतज़ार में ट्रिप अभी बाँटें", "Runs given out": "ट्रिप बाँट दी गईं", "No runs given out yet.": "अभी कोई ट्रिप नहीं बाँटी गई।",

  /* ---- admin ---- */
  "organisations": "संस्थाएँ", "runs in progress": "चल रही ट्रिप", "disposal records": "निपटान रिकॉर्ड", "collected so far": "अब तक उठाया", "Review now": "अभी देखें",
  "Worth a look before the next audit.": "अगले ऑडिट से पहले देख लें।", "Businesses": "कारोबारी", "Collectors": "कलेक्टर", "Admins": "एडमिन", "Revenue": "आमदनी",
  "Revenue and plans": "आमदनी और प्लान", "Invoices, payments and price list": "बिल, भुगतान और मूल्य सूची", "Collector invites": "कलेक्टर इन्वाइट", "Create collector invite": "कलेक्टर इन्वाइट बनाएँ",
  "Collector invite": "कलेक्टर इन्वाइट", "Note": "नोट", "Create code": "कोड बनाएँ", "Invite code": "इन्वाइट कोड", "Works for 7 days. Any number of collectors can join with it.": "7 दिन तक चलता है। इससे कितने भी कलेक्टर जुड़ सकते हैं।",
  "Revoke this code?": "यह कोड रद्द करें?", "It stops working right away. People who already joined keep their accounts.": "यह तुरंत काम करना बंद कर देगा। जो लोग जुड़ चुके हैं, उनके खाते बने रहेंगे।",
  "Revoke": "रद्द करें", "Code revoked": "कोड रद्द हो गया", "Works for 7 days, once.": "7 दिन तक, सिर्फ़ एक बार चलता है।",
  "Owner": "मालिक", "Decline": "अस्वीकार करें", "Withdraw verification": "जाँच वापस लें", "Check licence numbers against the official FSSAI records before you verify a business.": "कारोबार जाँचने से पहले लाइसेंस नंबर को सरकारी FSSAI रिकॉर्ड से मिलाएँ।",
  "Add facility": "प्लांट जोड़ें", "Edit facility": "प्लांट बदलें", "Hidden": "छिपा हुआ", "Capacity (kg)": "क्षमता (kg)", "Takes these routes": "ये रास्ते लेता है", "Has a valid certificate": "वैध प्रमाणपत्र है",
  "Required for Recover (C) and Packaging (D)": "रिकवर (C) और पैकेजिंग (D) के लिए ज़रूरी", "Certificate number": "प्रमाणपत्र नंबर", "Latitude": "अक्षांश", "Longitude": "देशांतर", "₹ per kg": "₹ प्रति kg",
  "+ they pay you, − gate fee": "+ वे आपको देते हैं, − गेट फ़ीस", "Certificate document": "प्रमाणपत्र दस्तावेज़", "No document uploaded yet.": "अभी कोई दस्तावेज़ अपलोड नहीं हुआ।",
  "PDF, PNG or JPEG, up to 5 MB. Businesses can open it from their pickup.": "PDF, PNG या JPEG, 5 MB तक। कारोबारी इसे अपने पिकअप से खोल सकते हैं।", "Save the facility first, then you can upload its certificate.": "पहले प्लांट सहेजें, फिर प्रमाणपत्र अपलोड करें।",
  "Give a password reset code": "पासवर्ड रीसेट कोड दें", "Reset code": "रीसेट कोड", "To verify": "जाँचने हैं", "Declined": "अस्वीकार",
  "New societies and businesses appear here when they sign up.": "नई सोसाइटी और कारोबारी साइन अप करते ही यहाँ दिखते हैं।", "No organisations in this list.": "इस सूची में कोई संस्था नहीं।",
  "Decline this organisation?": "यह संस्था अस्वीकार करें?", "They'll be told and won't get pickups.": "उन्हें बता दिया जाएगा और उन्हें पिकअप नहीं मिलेंगे।", "No facilities yet": "अभी कोई प्लांट नहीं",
  "Add the compost units, biogas plants, processors and feed makers you partner with. Matching only works with these.": "अपने साथी कंपोस्ट, बायोगैस, प्रोसेसर और चारा निर्माता जोड़ें। मिलान सिर्फ़ इन्हीं से होता है।",
  "Hide from matching": "मिलान से छिपाएँ", "Show in matching": "मिलान में दिखाएँ", "Saved": "सहेज लिया", "Choose a file first.": "पहले फ़ाइल चुनें।", "Certificate uploaded": "प्रमाणपत्र अपलोड हुआ", "Removed": "हटा दिया",
  "Search name, mobile or email": "नाम, मोबाइल या ईमेल खोजें", "No one found": "कोई नहीं मिला", "Try a different name or number.": "दूसरा नाम या नंबर आज़माएँ।", "Turn account on": "खाता चालू करें", "Turn account off": "खाता बंद करें",
  "Mode": "मोड",

  /* ---- billing ---- */
  "Plans": "प्लान", "Receipts": "रसीदें", "Receipt": "रसीद", "Bill": "बिल", "No bills yet": "अभी कोई बिल नहीं", "Your bills show up here after your free pickups are used.": "मुफ़्त पिकअप ख़त्म होने के बाद आपके बिल यहाँ दिखेंगे।",
  "Choose how you'd like to pay": "चुनें कि आप कैसे चुकाएँगे", "Choose how to pay": "चुनें कैसे चुकाना है", "How will you pay?": "आप कैसे चुकाएँगे?", "Pay per ride": "हर पिकअप पर चुकाएँ", "Pay after each pickup": "हर पिकअप के बाद चुकाएँ",
  "Billed on the weight confirmed at the hub": "हब पर पक्के हुए वज़न के हिसाब से बिल", "No monthly fee": "कोई मासिक फ़ीस नहीं", "Pay by UPI, card or net banking": "UPI, कार्ड या नेट बैंकिंग से चुकाएँ",
  "Best value": "सबसे किफ़ायती", "No pickup fee": "पिकअप का कोई शुल्क नहीं", "Change payment": "भुगतान का तरीक़ा बदलें", "Use pay per ride": "हर पिकअप पर चुकाना चुनें",
  "Pick pay per ride or a monthly plan below to start adding lots.": "लॉट जोड़ना शुरू करने के लिए नीचे “हर पिकअप पर चुकाएँ” या मासिक प्लान चुनें।",
  "Choose how you'd like to pay to keep adding lots.": "लॉट जोड़ते रहने के लिए चुनें कि कैसे चुकाएँगे।", "Choose how to pay to keep adding lots.": "लॉट जोड़ते रहने के लिए चुनें कैसे चुकाना है।",
  "After each pickup you'll get the fare and pay right away. We never store your card details.": "हर पिकअप के बाद भाड़ा मिलेगा और आप तुरंत चुका सकते हैं। हम आपके कार्ड की जानकारी नहीं रखते।",
  "UPI ID (optional)": "UPI आईडी (ज़रूरी नहीं)", "Saves typing it each time. You can change it when you pay.": "हर बार लिखने से बचाता है। चुकाते समय बदल सकते हैं।", "Save and continue": "सहेजें और आगे बढ़ें",
  "Payment ID": "भुगतान आईडी", "Your plan": "आपका प्लान", "Current plan": "मौजूदा प्लान", "Your current plan": "आपका मौजूदा प्लान", "Free trial": "मुफ़्त ट्रायल", "Your free trial is over": "आपका मुफ़्त ट्रायल ख़त्म हो गया",
  "Pick a plan to start adding lots.": "लॉट जोड़ना शुरू करने के लिए प्लान चुनें।", "Pay for your last pickup to keep adding lots.": "लॉट जोड़ते रहने के लिए पिछले पिकअप का भुगतान करें।", "You can't add new lots until this is paid.": "यह चुकाए बिना आप नए लॉट नहीं जोड़ सकते।",
  "See how you'll pay after that.": "देखें कि उसके बाद कैसे चुकाना है।", "Pay later": "बाद में चुकाएँ", "Pay another way": "दूसरे तरीक़े से चुकाएँ", "Your first": "आपके पहले",
  "pickups cost nothing. Pick how you'll pay after that, below.": "पिकअप मुफ़्त हैं। उसके बाद कैसे चुकाना है, नीचे चुनें।", "Pickup done, pay the fare": "पिकअप हो गया, भाड़ा चुकाएँ", "Paid. Thank you!": "चुका दिया। धन्यवाद!",
  "Scan with any UPI app (PhonePe, Google Pay, Paytm, BHIM). The amount is already filled in.": "किसी भी UPI ऐप (फ़ोनपे, गूगल पे, पेटीएम, BHIM) से स्कैन करें। रकम पहले से भरी है।",
  "UPI reference (optional)": "UPI रेफ़रेंस (ज़रूरी नहीं)", "It helps us match your payment faster.": "इससे हम आपका भुगतान जल्दी मिला पाते हैं।", "12-digit number from your app": "आपके ऐप का 12 अंकों का नंबर",
  "Only tap this after your UPI app shows success. We check every UPI payment against the bank.": "यह तभी दबाएँ जब आपका UPI ऐप सफल दिखा दे। हम हर UPI भुगतान बैंक से मिलाते हैं।",
  "Test payment": "टेस्ट भुगतान", "Simulated gateway: no real money moves.": "नक़ली गेटवे: असली पैसा नहीं कटता।", "Paying with": "इससे चुका रहे हैं:", "Your waste was collected and taken to the plant. Pay the fare to finish.": "आपका कचरा उठाकर प्लांट पहुँचा दिया गया। पूरा करने के लिए भाड़ा चुकाएँ।",
  "Payment failed.": "भुगतान नहीं हो सका।", "Couldn't load the payment window.": "भुगतान विंडो लोड नहीं हो सकी।", "Plan activated": "प्लान चालू हो गया", "Pay per ride is on. You'll pay after each pickup.": "हर पिकअप पर चुकाना चालू है। आप हर पिकअप के बाद चुकाएँगे।",
  "UPI": "UPI", "Pay with any UPI app. Usually the quickest.": "किसी भी UPI ऐप से चुकाएँ। आम तौर पर सबसे तेज़।", "Debit or credit card": "डेबिट या क्रेडिट कार्ड", "Enter your card when you pay.": "चुकाते समय अपना कार्ड डालें।",
  "Net banking": "नेट बैंकिंग", "Pay from your bank's website.": "अपने बैंक की वेबसाइट से चुकाएँ।", "Card": "कार्ड", "Test mode": "टेस्ट मोड", "Payments are simulated. No real money moves.": "भुगतान नक़ली हैं। असली पैसा नहीं कटता।",
  "Payments aren't switched on": "भुगतान चालू नहीं हैं", "Plans can't be bought right now.": "अभी प्लान नहीं ख़रीदे जा सकते।", "Demo QR": "डेमो QR", "per pickup": "प्रति पिकअप", "per kg": "प्रति kg", "Valid for 30 days": "30 दिन के लिए",
  "Price list": "मूल्य सूची", "Recent invoices": "हाल के बिल", "No invoices yet": "अभी कोई बिल नहीं", "They start once businesses finish their free trial.": "कारोबारियों का मुफ़्त ट्रायल ख़त्म होने के बाद ये शुरू होते हैं।",
  "UPI payments to check": "जाँचने वाले UPI भुगतान", "Not received": "नहीं मिला", "Received": "मिल गया", "Marked received": "मिला, दर्ज किया", "Sent back to the merchant as unpaid": "कारोबारी को “बाकी” बताकर वापस भेजा",
  "Merchants say they paid these by QR. Match each to your bank statement.": "कारोबारी कहते हैं कि इन्होंने QR से चुकाया। हर एक को अपने बैंक स्टेटमेंट से मिलाएँ।",
  "Base fee per pickup": "प्रति पिकअप बेस फ़ीस", "Price per month": "प्रति माह क़ीमत", "Included kg per month": "हर महीने शामिल kg", "Available to businesses": "कारोबारियों के लिए उपलब्ध", "₹ per kg by route": "रास्ते के हिसाब से ₹ प्रति kg",
  "per pickup + per kg": "प्रति पिकअप + प्रति kg", "Active monthly plan": "चालू मासिक प्लान",

  /* ---- compliance copilot ---- */
  "FSSAI Compliance Copilot": "FSSAI नियम सहायक", "FSSAI & Waste Copilot": "FSSAI और कचरा सहायक", "Compliance Copilot": "नियम सहायक", "Ask": "पूछें", "Ask Copilot →": "सहायक से पूछें →",
  "Ask the Regulatory Copilot": "नियम सहायक से पूछें", "Common regulatory inquiries:": "आम सवाल:", "Cattle feed restrictions": "पशु चारे पर रोक", "Cooked food holding limits": "पका खाना रखने की सीमा",
  "Section 59 penalties": "धारा 59 के दंड", "Spoiled produce routing": "सड़ी उपज का रास्ता", "FBO record keeping": "FBO रिकॉर्ड रखना",
  "Consult statutory RAG on food safety rules, swill feed bans & disposal laws.": "खाद्य सुरक्षा नियम, जूठन चारे पर रोक और निपटान क़ानूनों के बारे में पूछें।",
  "e.g. Can expired dairy or bread go to cattle feed?": "जैसे: क्या एक्सपायर्ड डेयरी या ब्रेड पशु चारे में जा सकती है?",
  "Can expired food go to cattle feed?": "क्या एक्सपायर्ड खाना पशु चारे में जा सकता है?", "What is the maximum holding time for cooked meals?": "पके खाने को रखने की अधिकतम अवधि क्या है?",

  /* ---- error and info messages from the server ---- */
  "Add the expiry date for this item.": "इस माल की एक्सपायरी की तारीख़ डालें।", "Admin accounts can't be deleted here.": "एडमिन खाते यहाँ से नहीं हटाए जा सकते।", "Check the per-kg rates.": "प्रति kg की दरें जाँचें।",
  "Check the price and quota.": "क़ीमत और कोटा जाँचें।", "Choose UPI, card or net banking.": "UPI, कार्ड या नेट बैंकिंग चुनें।", "Choose an item.": "माल चुनें।", "Choose how you will use FoodLoop.": "चुनें कि आप FoodLoop कैसे इस्तेमाल करेंगे।",
  "Couldn't reach the payment service.": "भुगतान सेवा तक नहीं पहुँच सके।", "Enter a quantity in kg.": "kg में मात्रा डालें।", "Enter a valid 10-digit mobile number.": "10 अंकों का सही मोबाइल नंबर डालें।",
  "Enter a valid date and time.": "सही तारीख़ और समय डालें।", "Enter a valid email address.": "सही ईमेल पता डालें।", "Enter both weights in kg.": "दोनों वज़न kg में डालें।", "Enter what your vehicle can carry, in kg.": "आपकी गाड़ी kg में कितना ले जा सकती है, डालें।",
  "Facility not found.": "प्लांट नहीं मिला।", "Invoice not found.": "बिल नहीं मिला।", "Lot not found.": "लॉट नहीं मिला।", "Mark the run collected first.": "पहले ट्रिप को “उठा लिया” दर्ज करें।", "Minimum can't be negative.": "न्यूनतम मात्रा शून्य से कम नहीं हो सकती।",
  "No certificate has been uploaded.": "कोई प्रमाणपत्र अपलोड नहीं हुआ।", "No record with that code.": "इस कोड का कोई रिकॉर्ड नहीं।", "Not a FoodLoop QR code.": "यह FoodLoop का QR कोड नहीं है।", "Not available.": "उपलब्ध नहीं।", "Not found.": "नहीं मिला।",
  "Nothing to pay on this invoice.": "इस बिल पर कुछ चुकाना नहीं है।", "There's nothing to pay on this bill.": "इस बिल पर कुछ चुकाना नहीं है।", "Nothing waiting to be checked.": "जाँचने के लिए कुछ नहीं है।", "Organisation not found.": "संस्था नहीं मिली।", "Person not found.": "व्यक्ति नहीं मिला।",
  "Pick at least one tier.": "कम से कम एक रास्ता चुनें।", "Pickup not found.": "पिकअप नहीं मिला।", "Plan not found.": "प्लान नहीं मिला।", "Please provide a question.": "कृपया सवाल लिखें।", "Please sign in to continue.": "आगे बढ़ने के लिए कृपया लॉग इन करें।", "Run not found.": "ट्रिप नहीं मिली।",
  "Start the payment first.": "पहले भुगतान शुरू करें।", "That account already exists.": "यह खाता पहले से है।", "That code is wrong or has expired.": "यह कोड ग़लत है या पुराना हो गया है।", "That file is too big. Keep it under 5 MB.": "फ़ाइल बहुत बड़ी है। 5 MB से कम रखें।",
  "That payment doesn't match this invoice.": "यह भुगतान इस बिल से मेल नहीं खाता।", "That plan isn't available.": "यह प्लान उपलब्ध नहीं है।", "The payment service refused the order.": "भुगतान सेवा ने ऑर्डर नहीं माना।", "This account has been turned off.": "यह खाता बंद कर दिया गया है।",
  "This account type is no longer in use.": "इस तरह का खाता अब चलन में नहीं है।", "This isn't available for your account.": "यह आपके खाते के लिए उपलब्ध नहीं है।", "This lot is already in a pickup.": "यह लॉट पहले से एक पिकअप में है।",
  "This run can't be accepted any more.": "यह ट्रिप अब स्वीकार नहीं की जा सकती।", "This run can't be handed back any more.": "यह ट्रिप अब वापस नहीं की जा सकती।", "This run can't be marked collected.": "इस ट्रिप को “उठा लिया” दर्ज नहीं किया जा सकता।",
  "This run can't be scheduled any more.": "इस ट्रिप का समय अब तय नहीं किया जा सकता।", "This run is assigned to another collector.": "यह ट्रिप दूसरे कलेक्टर को दी गई है।", "This run isn't yours.": "यह ट्रिप आपकी नहीं है।", "Unknown action.": "अनजानी कार्रवाई।",
  "Upload a PDF, PNG or JPEG file.": "PDF, PNG या JPEG फ़ाइल अपलोड करें।", "We couldn't confirm that payment.": "हम उस भुगतान की पुष्टि नहीं कर सके।", "Wrong mobile, email or password.": "मोबाइल, ईमेल या पासवर्ड ग़लत है।", "You already have a monthly plan.": "आपके पास पहले से मासिक प्लान है।",
  "Your account is waiting for approval.": "आपका खाता मंज़ूरी का इंतज़ार कर रहा है।", "Your current password is wrong.": "आपका मौजूदा पासवर्ड ग़लत है।", "Your password is wrong.": "आपका पासवर्ड ग़लत है।",
  "Pick a time from now up to 14 days ahead.": "अभी से 14 दिन के अंदर का समय चुनें।", "This run is already taken by another collector.": "यह ट्रिप किसी दूसरे कलेक्टर ने ले ली है।",

  /* ---- notification titles ---- */
  "Pickup planned": "पिकअप तय हुआ", "Pickup time set": "पिकअप का समय तय हुआ", "Waste collected": "कचरा उठा लिया गया", "Disposal record ready": "निपटान रिकॉर्ड तैयार", "Collector changed": "कलेक्टर बदला",
  "New run assigned": "नई ट्रिप मिली", "New business to verify": "जाँचने के लिए नया कारोबारी", "New invoice": "नया बिल", "Payment not received": "भुगतान नहीं मिला", "Payment received": "भुगतान मिल गया", "You're verified": "आपकी जाँच हो गई",
  "A new time will be confirmed.": "नया समय पक्का किया जाएगा।",
});

/* text with numbers or names in it */
const _R = (re, rep) => I18N.hiRe.push([re, rep]);
Object.assign(I18N.hi, {
  "Accept": "स्वीकारें", "Total": "कुल", "UPI ·": "UPI ·", "· UTR": "· UTR", "· no UTR given": "· UTR नहीं दिया", "· expiry": "· एक्सपायरी", "kg included": "kg शामिल",
  "kg of waste every month": "kg कचरा हर महीने", "Extra kg at": "ज़्यादा kg पर", "per kg, any waste type": "प्रति kg, किसी भी तरह का कचरा", "per kg by waste type": "प्रति kg, कचरे के प्रकार के हिसाब से",
  "This points to a demo UPI ID, so scanning it moves no money. Set UPI_VPA in .env to use your own.": "यह डेमो UPI आईडी की ओर जाता है, इसलिए स्कैन करने पर पैसा नहीं कटता। अपनी आईडी के लिए .env में UPI_VPA सेट करें।",
  "No real money moves. Test card 4111 1111 1111 1111 (any future date and CVV) or UPI success@razorpay.": "असली पैसा नहीं कटता। टेस्ट कार्ड 4111 1111 1111 1111 (कोई भी आगे की तारीख़ और CVV) या UPI success@razorpay इस्तेमाल करें।",
  "A FoodLoop admin adds partner facilities. Until then, nothing can be matched.": "FoodLoop एडमिन साथी प्लांट जोड़ता है। तब तक कोई मिलान नहीं हो सकता।",
  "Open my UPI app": "मेरा UPI ऐप खोलें", "Open PDF": "PDF खोलें", "Plan pickup runs": "पिकअप ट्रिप बनाएँ", "Set pickup time": "पिकअप का समय तय करें",
  "Confirm time": "समय पक्का करें", "Mark as collected": "उठा लिया, ऐसा लिखें", "Show UPI QR": "UPI QR दिखाएँ", "Consult Copilot": "सहायक से पूछें",
  "Verified Safe Route": "जाँचा हुआ सुरक्षित रास्ता", "Mandatory Routing Law Applied": "ज़रूरी रास्ते का नियम लागू",
  "Official Statutory Index": "सरकारी नियमों की सूची", "Statutory Citations:": "नियमों के हवाले:", "Engine:": "इंजन:",
  "Order placed": "ऑर्डर दिया गया", "kg": "kg", "km": "km",
});
_R(/^Record (\S+) issued$/, "रिकॉर्ड $1 जारी हुआ");
_R(/^(.+) of (.+) will go to (.+)\. We'll include it in the next pickup run\.$/, "$1 का $2 $3 में जाएगा। इसे अगली पिकअप ट्रिप में शामिल किया जाएगा।");
_R(/^Run #(\d+)$/, "ट्रिप #$1");
_R(/^Run #(\d+) · (.+)$/, "ट्रिप #$1 · $2");
_R(/^Pickup #(\d+)$/, "पिकअप #$1");
_R(/^Pickup #(\d+) is done$/, "पिकअप #$1 पूरा हुआ");
_R(/^Pickup #(\d+) · to pay$/, "पिकअप #$1 · चुकाना है");
_R(/^Pickup #(\d+) · (.+)$/, "पिकअप #$1 · $2");
_R(/^(\d+) min ago$/, "$1 मिनट पहले");
_R(/^(\d+) h ago$/, "$1 घंटे पहले");
_R(/^Yesterday, (.+)$/, "कल, $1");
_R(/^Good (morning|afternoon|evening),? (.+)$/, "नमस्ते, $2");
_R(/^Expected (.+)$/, "अपेक्षित: $1");
_R(/^Route \(([\d.]+) km\)$/, "रास्ता ($1 km)");
_R(/^([\d.]+) km round trip \(road estimate\) · (\d+) stops? · ([\d.]+) kg$/, "$1 km आना-जाना (सड़क का अनुमान) · $2 स्टॉप · $3 kg");
_R(/^Base (.+) \+ distance (.+) \+ extra stops (.+) \+ weight (.+)$/, "बेस $1 + दूरी $2 + अतिरिक्त स्टॉप $3 + वज़न $4");
_R(/^Accept · (.+)$/, "स्वीकारें · $1");
_R(/^(.+) per km$/, "$1 प्रति km");
_R(/^Pick up: (.+)$/, "यहाँ से उठाना है: $1");
_R(/^(\d+) runs?$/, "$1 ट्रिप");
_R(/^(.+) earned in last 7 days$/, "पिछले 7 दिनों में कमाए: $1");
_R(/^([\d.,]+ kg) · (\d+) stops? · ([\d.]+) km round trip$/, "$1 · $2 स्टॉप · $3 km आना-जाना");
_R(/^To (.+)$/, "$1 को");
_R(/^(\d+) organisations? to verify$/, "$1 संस्था जाँचनी है");
_R(/^(\d+) runs? with a weight mismatch$/, "$1 ट्रिप में वज़न का अंतर");
_R(/^Pay (₹\s?[\d,.]+) by UPI$/, "UPI से $1 चुकाएँ");
_R(/^Pay (₹\s?[\d,.]+) \(test\)$/, "$1 चुकाएँ (टेस्ट)");
_R(/^I've paid (₹\s?[\d,.]+)$/, "मैंने $1 चुका दिए");
_R(/^Pay (₹\s?[\d,.]+)$/, "$1 चुकाएँ");
_R(/^(₹\s?[\d,.]+) to pay$/, "$1 चुकाना है");
_R(/^Free trial: (\d+) of (\d+) pickups left$/, "मुफ़्त ट्रायल: $2 में से $1 पिकअप बचे");
_R(/^(\d+) of (\d+) pickups left$/, "$2 में से $1 पिकअप बचे");
_R(/^Runs until (.+)\. (.+) of (.+) kg used\.$/, "$1 तक चलेगा। $3 kg में से $2 kg इस्तेमाल हुए।");
_R(/^Weigh and close run #(\d+)$/, "ट्रिप #$1 तौलें और पूरा करें");
_R(/^Pickup time for run #(\d+)$/, "ट्रिप #$1 के पिकअप का समय");
_R(/^Merchant bills · run #(\d+)$/, "कारोबारियों के बिल · ट्रिप #$1");
_R(/^Expected (.+)\. Enter what the hub scale and the facility scale showed\. A difference over 5% is flagged on the record\.$/, "अपेक्षित: $1। हब और प्लांट के तराज़ू पर जो वज़न दिखा, वह डालें। 5% से ज़्यादा अंतर रिकॉर्ड में दर्ज होगा।");
_R(/^You're joining (.+) as a collector\.$/, "आप $1 से कलेक्टर के रूप में जुड़ रहे हैं।");
_R(/^Give this to (.+)\. It works for (\d+) minutes\.$/, "यह $1 को दें। यह $2 मिनट चलता है।");
_R(/^Your code is (.+)\. This is never shown in production\.$/, "आपका कोड $1 है। यह असली ऐप में नहीं दिखता।");
_R(/^Your FoodLoop collector invite code is (.+)$/, "आपका FoodLoop कलेक्टर इन्वाइट कोड $1 है।");
_R(/^(.+) will go to (.+)\. We'll include it in the next pickup run\.$/, "$1 $2 में जाएगा। इसे अगली पिकअप ट्रिप में शामिल किया जाएगा।");
_R(/^(\d+) new$/, "$1 नई");
_R(/^(\d+) lots?$/, "$1 लॉट");
_R(/^(\d+) stops?$/, "$1 स्टॉप");
_R(/^received \((\d+) payments?\)$/, "मिले ($1 भुगतान)");
_R(/^unpaid \((\d+)\)$/, "बाकी ($1)");
_R(/^driver fares \((\d+) closed runs?\)$/, "ड्राइवर भाड़ा ($1 पूरी ट्रिप)");
_R(/^(\d+) active monthly plans?$/, "$1 चालू मासिक प्लान");
_R(/^(.+) · used (\d+) times?(?: · expires (.+))?$/, "$1 · $2 बार इस्तेमाल · $3 को ख़त्म");
_R(/^expires (.+)$/, "$1 को ख़त्म");
_R(/^· expires (.+)$/, "· $1 को ख़त्म");
_R(/^Mode: (.+)$/, "मोड: $1");
_R(/^Why: (.+)$/, "वजह: $1");
_R(/^([\d.,]+) kg\*? \(placeholder factor\)\.$/, "$1 kg* (अनुमानित आँकड़ा)।");
_R(/^CO₂e avoided so far: about (.+) kg\* \(placeholder factor\)\.$/, "अब तक बचा CO₂e: लगभग $1 kg* (अनुमानित आँकड़ा)।");
_R(/^(\d+) waiting for pickup \((\d+) lots?\)$/, "$1 kg पिकअप के इंतज़ार में ($2 लॉट)");
_R(/^Pickup #(\d+) was collected\.$/, "पिकअप #$1 उठा लिया गया।");
_R(/^A pickup of your lots is planned \(#(\d+)\)\.$/, "आपके लॉट का पिकअप तय हुआ है (#$1)।");
_R(/^Record (\S+) is available\.$/, "रिकॉर्ड $1 तैयार है।");
_R(/^Pickup #(\d+): Rs ([\d.]+) to pay\.$/, "पिकअप #$1: Rs $2 चुकाना है।");
_R(/^Run #(\d+): (.+) kg, (\d+) stops?, about Rs (\d+) for the trip\.$/, "ट्रिप #$1: $2 kg, $3 स्टॉप, इस सफ़र के लिए लगभग Rs $4।");
_R(/^Pickup #(\d+) has a new collector\. A new time will be confirmed\.$/, "पिकअप #$1 का कलेक्टर बदल गया है। नया समय पक्का किया जाएगा।");
_R(/^That (.+) is already in use\.$/, "यह $1 पहले से इस्तेमाल में है।");
_R(/^(.+) is required\.$/, "$1 ज़रूरी है।");
_R(/^No order found with that ID\. Check it (.*)$/, "इस आईडी का कोई ऑर्डर नहीं मिला। इसे जाँचें $1");
