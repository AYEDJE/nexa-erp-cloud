(function () {
  'use strict';

  const LANGS = {
    fr: { label: '🇫🇷 FR',        dir: 'ltr', locale: 'fr-FR' },
    en: { label: '🇬🇧 EN',        dir: 'ltr', locale: 'en-GB' },
    ar: { label: '🇹🇳 AR (عربي)', dir: 'rtl', locale: 'ar-TN-u-nu-latn' }
  };

  /* ---------- Dictionnaire : [français, anglais, arabe] ---------- */
  const PHRASES = [
    // Marque
    ["Votre gestion, notre solution", "Your management, our solution", "إدارتكم، حلّنا"],
    ["Votre gestion, Notre solution", "Your management, our solution", "إدارتكم، حلّنا"],

    // Navigation
    ["Tableau de bord", "Dashboard", "لوحة التحكم"],
    ["Ventes & Factures", "Sales & Invoices", "المبيعات والفواتير"],
    ["Produits & Articles", "Products & Items", "المنتجات والمخزون"],
    ["Clients", "Customers", "العملاء"],
    ["Achats", "Purchases", "المشتريات"],
    ["Paiements & Trésorerie", "Payments & Treasury", "المدفوعات والخزينة"],
    ["Fournisseurs", "Suppliers", "الموردون"],
    ["Stock & Entrepôts", "Stock & Warehouses", "المخزون والمستودعات"],
    ["Rapports & Stats", "Reports & Stats", "التقارير والإحصائيات"],
    ["PARAMÈTRES", "SETTINGS", "الإعدادات"],
    ["Société", "Company", "الشركة"],
    ["Utilisateurs & Rôles", "Users & Roles", "المستخدمون والأدوار"],
    ["Paramètres généraux", "General Settings", "الإعدادات العامة"],

    // Topbar
    ["Dashboard", "Dashboard", "الرئيسية"],
    ["Produits", "Products", "المنتجات"],
    ["Factures", "Invoices", "الفواتير"],
    ["Utilisateurs", "Users", "المستخدمون"],
    ["Déconnexion", "Logout", "تسجيل الخروج"],
    ["Administrateur", "Administrator", "مدير"],
    ["Mode Démo", "Demo Mode", "وضع تجريبي"],
    ["Retourner au Tableau de bord", "Back to Dashboard", "العودة إلى لوحة التحكم"],
    ["Catalogue Produits", "Product Catalog", "كتالوج المنتجات"],
    ["Gérer les clients", "Manage customers", "إدارة العملاء"],
    ["Gérer les utilisateurs", "Manage users", "إدارة المستخدمين"],

    // Dashboard
    ["Chiffre d'affaires", "Revenue", "إجمالي المبيعات"],
    ["Factures en attente", "Pending Invoices", "فواتير معلقة"],
    ["Rupture de stock", "Out of Stock", "نفاد المخزون"],
    ["Collaborateurs", "Collaborators", "فريق العمل"],
    ["Gérer les produits →", "Manage items →", "إدارة المنتجات ←"],
    ["Voir les ventes →", "View sales →", "عرض المبيعات ←"],
    ["Consulter →", "Review →", "مراجعة ←"],
    ["Vérifier le stock →", "Check stock →", "فحص المخزون ←"],
    ["Gérer l'équipe →", "Manage team →", "إدارة الفريق ←"],
    ["Valeur du stock par produit", "Stock value by product", "قيمة المخزون حسب المنتج"],
    ["Répartition des factures", "Invoice distribution", "توزيع الفواتير"],

    // Produits
    ["Produits & Catalogue", "Products & Catalog", "المنتجات والكتالوج"],
    ["Catalogue des articles en vente", "Catalog of items for sale", "كتالوج المواد المعروضة للبيع"],
    ["Nouveau Produit", "New Product", "منتج جديد"],
    ["ID", "ID", "المعرف"],
    ["Désignation", "Item Name", "اسم المنتج"],
    ["Description", "Description", "الوصف"],
    ["Prix unitaire", "Unit Price", "سعر الوحدة"],
    ["Stock disponible", "Available Stock", "الكمية المتوفرة"],
    ["Actions", "Actions", "الإجراءات"],
    ["Ajouter un nouveau produit", "Add a new product", "إضافة منتج جديد"],
    [`Aucun produit trouvé. Cliquez sur "Nouveau Produit" pour en créer un.`, `No product found. Click "New Product" to create one.`, `لا توجد منتجات. اضغط على "منتج جديد" لإنشاء واحد.`],

    // Factures — page
    ["Ventes & Facturation", "Sales & Invoicing", "المبيعات والفوترة"],
    ["Liste des factures et devis émis", "List of issued invoices and quotes", "قائمة الفواتير وعروض الأسعار الصادرة"],
    ["Nouvelle Facture", "New Invoice", "فاتورة جديدة"],
    ["Total Facturé (TTC)", "Total Invoiced (Incl. Tax)", "إجمالي الفوترة (شامل الضريبة)"],
    ["Factures Payées", "Paid Invoices", "فواتير مسددة"],
    ["Factures En Attente / Brouillons", "Pending Invoices / Drafts", "فواتير قيد الانتظار / مسودات"],
    ["N° Document", "Doc #", "رقم الوثيقة"],
    ["Type", "Type", "النوع"],
    ["Client", "Customer", "العميل"],
    ["Total HT", "Total Excl. Tax", "المجموع دون ضريبة"],
    ["Total TTC", "Total Incl. Tax", "المجموع شامل الضريبة"],
    ["Statut", "Status", "الحالة"],
    ["Brouillon", "Draft", "مسودة"],
    ["Payée", "Paid", "مسددة"],
    ["En attente", "Pending", "قيد الانتظار"],
    ["Client anonyme", "Anonymous customer", "عميل مجهول"],
    ["Régler", "Pay", "تسديد"],
    ["Régler cette facture", "Pay this invoice", "تسديد هذه الفاتورة"],
    ["PDF", "PDF", "PDF"],
    ["Télécharger le PDF officiel", "Download the official PDF", "تنزيل ملف PDF الرسمي"],
    ["Génération...", "Generating...", "جارٍ الإنشاء..."],
    ["Chargement des factures...", "Loading invoices...", "جارٍ تحميل الفواتير..."],
    ["Téléchargement PDF en direct avec montant en toutes lettres", "Live PDF download with amount in words", "تنزيل PDF مباشر مع المبلغ كتابةً"],
    [`Aucune facture trouvée. Cliquez sur "Nouvelle Facture" pour en créer une.`, `No invoice found. Click "New Invoice" to create one.`, `لا توجد فواتير. اضغط على "فاتورة جديدة" لإنشاء واحدة.`],

    // Factures — modale création
    ["Émettre une facture", "Issue an invoice", "إصدار فاتورة"],
    ["Type de document", "Document type", "نوع الوثيقة"],
    ["Facture de Vente", "Sales Invoice", "فاتورة بيع"],
    ["Devis Commercial", "Commercial Quote", "عرض سعر تجاري"],
    ["Bon de Commande", "Purchase Order", "أمر شراء"],
    ["Langue du document", "Document language", "لغة الوثيقة"],
    ["Français (FR)", "French (FR)", "الفرنسية (FR)"],
    ["Anglais (EN)", "English (EN)", "الإنجليزية (EN)"],
    ["Arabe (AR)", "Arabic (AR)", "العربية (AR)"],
    ["Nom du client *", "Customer name *", "اسم العميل *"],
    ["Email client", "Customer email", "البريد الإلكتروني للعميل"],
    ["Ligne de produit ou service", "Product or service line", "بند المنتج أو الخدمة"],
    ["Désignation de la prestation / article *", "Service / item description *", "وصف الخدمة / المنتج *"],
    ["Quantité *", "Quantity *", "الكمية *"],
    ["Prix unitaire HT (€) *", "Unit price excl. tax (€) *", "سعر الوحدة دون ضريبة (€) *"],
    ["Taux TVA (%)", "VAT rate (%)", "نسبة الضريبة (%)"],
    ["Conditions de règlement", "Payment terms", "شروط الدفع"],
    ["Paiement à 30 jours", "Payment within 30 days", "الدفع خلال 30 يومًا"],
    ["Créer et Générer la Facture", "Create and Generate Invoice", "إنشاء الفاتورة وتوليدها"],
    ["Ex: Société Alpha SARL", "e.g. Alpha Company LLC", "مثال: شركة ألفا ش.م.م"],
    ["Ex: Licence ERP Cloud - 1 An", "e.g. ERP Cloud License - 1 Year", "مثال: ترخيص ERP سحابي - سنة"],
    ["Ex: 450.00", "e.g. 450.00", "مثال: 450.00"],

    // Paiement (modale)
    ["Régler la facture", "Pay invoice", "تسديد الفاتورة"],
    ["Client :", "Customer:", "العميل:"],
    ["Montant à régler (TTC)", "Amount to pay (incl. tax)", "المبلغ المستحق (شامل الضريبة)"],
    ["Moyen de paiement", "Payment method", "وسيلة الدفع"],
    ["Encaissement manuel", "Manual collection", "تحصيل يدوي"],
    ["Espèces", "Cash", "نقدًا"],
    ["Virement bancaire", "Bank transfer", "تحويل بنكي"],
    ["Chèque", "Cheque", "شيك"],
    ["Mobile Money (reçu)", "Mobile Money (received)", "موبايل موني (مستلم)"],
    ["Paiement en ligne", "Online payment", "دفع إلكتروني"],
    ["Carte / Mobile Money en ligne", "Card / Mobile Money online", "بطاقة / موبايل موني إلكترونيًا"],
    ["Date du paiement", "Payment date", "تاريخ الدفع"],
    ["Référence", "Reference", "المرجع"],
    ["N° chèque, ID transaction...", "Cheque no., transaction ID...", "رقم الشيك، رقم العملية..."],
    ["Enregistrer le paiement", "Record payment", "تسجيل الدفعة"],
    ["Payer en ligne", "Pay online", "الدفع إلكترونيًا"],
    ["Vous allez être redirigé vers la page de paiement sécurisée. La facture passera en « Payée » automatiquement une fois le paiement confirmé.",
     "You will be redirected to the secure payment page. The invoice will automatically be marked “Paid” once the payment is confirmed.",
     "سيتم تحويلك إلى صفحة الدفع الآمنة. ستصبح الفاتورة «مسددة» تلقائيًا بعد تأكيد الدفع."],

    // Utilisateurs
    ["Gestion des Collaborateurs & Accès", "Team & Access Management", "إدارة المستخدمين والصلاحيات"],
    ["Comptes & Permissions de l'Entreprise", "Company Accounts & Permissions", "حسابات الشركة وصلاحيات الوصول"],
    ["Contrôle RBAC à 6 niveaux de permission", "RBAC control with 6 permission levels", "تحكم RBAC بستة مستويات من الصلاحيات"],
    ["Inscrire un Utilisateur", "Register User", "تسجيل مستخدم جديد"],
    ["Total Utilisateurs", "Total Users", "إجمالي المستخدمين"],
    ["Collaborateurs Internes", "Internal Staff", "الموظفون الداخليون"],
    ["Portails Tiers (Clients/Fournisseurs)", "Third-party Portals (Customers/Suppliers)", "بوابات الشركاء (عملاء/موردون)"],
    ["Sécurité 2FA / MFA Active", "Active 2FA / MFA", "المصادقة الثنائية 2FA مفعلة"],
    ["Email / Identifiant", "Email / Identifier", "البريد / المعرف"],
    ["Rôle Fonctionnel", "Assigned Role", "الدور الوظيفي"],
    ["Périmètre", "Scope", "النطاق"],
    ["Sécurité 2FA", "2FA Security", "أمان 2FA"],
    ["Actif", "Active", "نشط"],
    ["Désactivé", "Disabled", "معطّل"],
    ["Désactiver", "Disable", "تعطيل"],
    ["Réactiver", "Re-enable", "إعادة التفعيل"],
    ["Changer l'état du compte", "Change account status", "تغيير حالة الحساب"],
    ["Portail Externe", "External Portal", "بوابة خارجية"],
    ["Interne Entreprise", "Company Internal", "داخلي للشركة"],
    ["Non configuré", "Not configured", "غير مهيأ"],
    ["Activé", "Enabled", "مفعّل"],
    ["Collaborateur", "Staff", "موظف"],
    ["Portail Tiers", "Third-party Portal", "بوابة الشركاء"],
    ["Magasinier", "Storekeeper", "أمين مخزن"],
    ["Commercial", "Sales", "مبيعات"],
    ["Finance", "Finance", "مالية"],
    ["Admin", "Admin", "مدير"],
    ["Chargement des comptes...", "Loading accounts...", "جارٍ تحميل الحسابات..."],
    [`Aucun utilisateur trouvé. Cliquez sur "Inscrire un Utilisateur" pour débuter.`, `No user found. Click "Register User" to get started.`, `لا يوجد مستخدمون. اضغط على "تسجيل مستخدم جديد" للبدء.`],
    ["Inscrire un collaborateur ou tiers", "Register a team member or third party", "تسجيل موظف أو طرف خارجي"],
    ["Email professionnel de connexion *", "Professional login email *", "البريد المهني لتسجيل الدخول *"],
    ["Rôle & Profil fonctionnel (selon le cahier des charges) *", "Role & functional profile *", "الدور والملف الوظيفي *"],
    ["Profils Collaborateurs Internes", "Internal Staff Profiles", "ملفات الموظفين الداخليين"],
    ["Portails Utilisateurs Externes Sécurisés", "Secure External User Portals", "بوابات المستخدمين الخارجيين الآمنة"],
    ["💼 Responsable Commercial (Devis, Ventes, Facturation)", "💼 Sales Manager (Quotes, Sales, Invoicing)", "💼 مسؤول المبيعات (عروض، مبيعات، فوترة)"],
    ["💰 Responsable Financier et Comptable (Trésorerie, OCR)", "💰 Finance & Accounting Manager (Treasury, OCR)", "💰 مسؤول مالي ومحاسبي (خزينة، OCR)"],
    ["📦 Responsable des Stocks et Magasinier (Entrepôts)", "📦 Stock Manager & Storekeeper (Warehouses)", "📦 مسؤول المخزون وأمين المخزن (مستودعات)"],
    ["🛒 Responsable des Achats (Fournisseurs, BC)", "🛒 Purchasing Manager (Suppliers, POs)", "🛒 مسؤول المشتريات (موردون، أوامر شراء)"],
    ["👤 Collaborateur Standard (Consultation)", "👤 Standard Staff (Read-only)", "👤 موظف عادي (اطلاع فقط)"],
    ["🔒 Administrateur Adjoint (Tous droits)", "🔒 Deputy Administrator (Full rights)", "🔒 مدير مساعد (كل الصلاحيات)"],
    ["🌐 Client Partenaire (Consultation Devis/Factures)", "🌐 Partner Customer (View Quotes/Invoices)", "🌐 عميل شريك (اطلاع على العروض/الفواتير)"],
    ["🏭 Fournisseur Agréé (Bons de Commande)", "🏭 Approved Supplier (Purchase Orders)", "🏭 مورد معتمد (أوامر الشراء)"],
    ["Mot de passe initial *", "Initial password *", "كلمة المرور الأولية *"],
    ["Confirmer mot de passe *", "Confirm password *", "تأكيد كلمة المرور *"],
    ["Exiger le renouvellement du mot de passe à la 1ère connexion", "Require password change on first login", "إلزام تغيير كلمة المرور عند أول تسجيل دخول"],
    ["Créer et Activer le compte", "Create and Activate account", "إنشاء الحساب وتفعيله"],
    ["collaborateur@entreprise.com", "colleague@company.com", "colleague@company.com"],

    // Connexion
    ["Connexion", "Login", "تسجيل الدخول"],
    ["Email professionnel", "Professional email", "البريد المهني"],
    ["Mot de passe", "Password", "كلمة المرور"],
    ["Se connecter", "Sign in", "تسجيل الدخول"],
    ["Pas encore de compte ?", "No account yet?", "ليس لديك حساب بعد؟"],
    ["Créer un espace entreprise →", "Create a company space →", "إنشاء مساحة للشركة ←"],
    ["Nouvelle entreprise ?", "New company?", "شركة جديدة؟"],
    ["Créer un compte ERP →", "Create an ERP account →", "إنشاء حساب ERP ←"],
    ["Impossible de joindre le serveur backend.", "Unable to reach the backend server.", "تعذّر الاتصال بالخادم."],
    ["Erreur de connexion.", "Login error.", "خطأ في تسجيل الدخول."],

    // Inscription entreprise
    ["Déployez votre ERP d'Entreprise en quelques minutes.", "Deploy your enterprise ERP in minutes.", "انشر نظام ERP لشركتك في دقائق."],
    ["Créer un nouvel espace Entreprise", "Create a new Company space", "إنشاء مساحة شركة جديدة"],
    ["Complétez les informations légales pour configurer votre environnement ERP.", "Fill in the legal information to set up your ERP environment.", "أكمل المعلومات القانونية لإعداد بيئة ERP الخاصة بك."],
    ["Identité de votre Entreprise", "Your Company Identity", "هوية شركتك"],
    ["Raison Sociale / Nom légal *", "Legal name *", "الاسم القانوني *"],
    ["Forme Juridique", "Legal form", "الشكل القانوني"],
    ["Identifiant Cloud Unique (Nom de domaine ERP) *", "Unique Cloud ID (ERP domain name) *", "المعرّف السحابي الفريد (نطاق ERP) *"],
    ["Matricule Fiscal / N° TVA", "Tax ID / VAT No.", "المعرّف الجبائي / رقم الضريبة"],
    ["Secteur d'activité", "Business sector", "قطاع النشاط"],
    ["Compte Administrateur Client (Détenteur Principal)", "Customer Administrator Account (Main Owner)", "حساب مدير العميل (المالك الرئيسي)"],
    ["Nom & Prénom de l'Administrateur *", "Administrator full name *", "الاسم الكامل للمدير *"],
    ["Email professionnel de connexion *", "Professional login email *", "البريد المهني لتسجيل الدخول *"],
    ["Mot de passe de sécurité *", "Security password *", "كلمة مرور الأمان *"],
    ["Confirmer le mot de passe *", "Confirm password *", "تأكيد كلمة المرور *"],
    ["Minimum 8 caractères", "Minimum 8 characters", "8 أحرف على الأقل"],
    ["Abonnement SaaS & Justificatif KYC", "SaaS Subscription & KYC Document", "اشتراك SaaS ووثيقة KYC"],
    ["Choisissez votre formule de démarrage :", "Choose your starting plan:", "اختر باقة البداية:"],
    ["Essai Gratuit", "Free Trial", "تجربة مجانية"],
    ["Pack Business", "Business Pack", "باقة الأعمال"],
    ["Entreprise Cloud", "Cloud Enterprise", "الشركات السحابية"],
    ["Populaire", "Popular", "الأكثر شيوعًا"],
    ["Déployer mon Espace Entreprise ERP", "Deploy my ERP Company Space", "نشر مساحة شركتي ERP"],
    ["Déploiement en cours...", "Deployment in progress...", "جارٍ النشر..."],
    ["Votre entreprise est déjà enregistrée ?", "Is your company already registered?", "هل شركتك مسجلة بالفعل؟"],
    ["Se connecter à l'espace de gestion →", "Sign in to the management space →", "تسجيل الدخول إلى مساحة الإدارة ←"],
    ["Les deux mots de passe ne correspondent pas.", "The two passwords do not match.", "كلمتا المرور غير متطابقتين."],
    ["Le mot de passe doit contenir au moins 8 caractères.", "The password must contain at least 8 characters.", "يجب أن تحتوي كلمة المرور على 8 أحرف على الأقل."],
    ["L'identifiant cloud est obligatoire.", "The cloud ID is required.", "المعرّف السحابي إلزامي."],

    // Messages génériques
    ["Chargement...", "Loading...", "جارٍ التحميل..."],
    ["Enregistrer", "Save", "حفظ"],
    ["Annuler", "Cancel", "إلغاء"],
    ["Supprimer", "Delete", "حذف"],
    ["Modifier", "Edit", "تعديل"],
    ["Fermer", "Close", "إغلاق"],
    ["Rechercher", "Search", "بحث"],
    ["Nouveau Client", "New Customer", "عميل جديد"],
    ["Nom", "Name", "الاسم"],
    ["Email", "Email", "البريد الإلكتروني"],
    ["Téléphone", "Phone", "الهاتف"],
    ["Adresse", "Address", "العنوان"],
    ["Prix", "Price", "السعر"],
    ["Stock", "Stock", "المخزون"],

    ["Ma Société", "My Company", "شركتي"],
    ["Ces informations apparaissent sur tous vos documents (factures, devis, bons de livraison…).", "This information appears on all your documents (invoices, quotes, delivery notes…).", "تظهر هذه المعلومات على جميع وثائقك (فواتير، عروض أسعار، سندات تسليم…)."],
    ["Identité de la société", "Company identity", "هوية الشركة"],
    ["Raison sociale", "Company name", "الاسم التجاري"],
    ["Forme juridique", "Legal form", "الشكل القانوني"],
    ["Activité", "Activity", "النشاط"],
    ["Coordonnées", "Contact details", "بيانات الاتصال"],
    ["Adresse", "Address", "العنوان"],
    ["Ville", "City", "المدينة"],
    ["Pays", "Country", "البلد"],
    ["Téléphone", "Phone", "الهاتف"],
    ["Site web", "Website", "الموقع الإلكتروني"],
    ["Informations légales et fiscales", "Legal and tax information", "المعلومات القانونية والجبائية"],
    ["Matricule fiscal / N° TVA *", "Tax ID / VAT No. *", "المعرّف الجبائي / رقم الضريبة *"],
    ["Lieu d'émission des documents *", "Place of issue of documents *", "مكان إصدار الوثائق *"],
    ["Registre de commerce (RC)", "Trade register (RC)", "السجل التجاري"],
    ["Valeurs par défaut des factures", "Invoice defaults", "القيم الافتراضية للفواتير"],
    ["Taux de TVA par défaut (%)", "Default VAT rate (%)", "نسبة الضريبة الافتراضية (%)"],
    ["Conditions de règlement par défaut", "Default payment terms", "شروط الدفع الافتراضية"],
    ["Coordonnées bancaires", "Bank details", "البيانات البنكية"],
    ["Banque", "Bank", "البنك"],
    ["Code SWIFT / BIC", "SWIFT / BIC code", "رمز SWIFT / BIC"],
    ["Les coordonnées bancaires figurent sur la facture si Banque, RIB et IBAN sont tous renseignés.", "Bank details appear on the invoice if Bank, RIB and IBAN are all filled in.", "تظهر البيانات البنكية على الفاتورة إذا تم ملء البنك وRIB وIBAN."],
    ["Enregistrer les informations", "Save information", "حفظ المعلومات"],
    ["Profil complet : vous pouvez émettre des factures.", "Profile complete: you can issue invoices.", "الملف مكتمل: يمكنك إصدار الفواتير."],
    ["Profil incomplet", "Incomplete profile", "الملف غير مكتمل"],
    ["à renseigner pour émettre des factures :", "to fill in to issue invoices:", "يجب استكماله لإصدار الفواتير:"],
    ["La raison sociale est obligatoire.", "The company name is required.", "الاسم التجاري إلزامي."],
    ["Informations de la société enregistrées avec succès.", "Company information saved successfully.", "تم حفظ معلومات الشركة بنجاح."],
    ["Informations enregistrées (mode démo).", "Information saved (demo mode).", "تم حفظ المعلومات (وضع تجريبي)."],
    ["Matricule fiscal *", "Tax ID *", "المعرّف الجبائي *"],
  ];

  /* ---------- Messages dynamiques (alertes, erreurs) avec {variables} ---------- */
  const MESSAGES = {
    fr: {
      invoice_created: "Facture {number} générée avec succès !",
      user_created: "Utilisateur \"{email}\" inscrit avec succès !",
      client_saved: "Client \"{name}\" enregistré avec succès !",
      payment_saved: "Paiement enregistré : la facture est marquée comme payée.",
      payment_success: "Paiement reçu. La facture sera marquée « Payée » dès la confirmation du prestataire.",
      payment_cancel: "Paiement annulé. La facture reste en attente.",
      error_prefix: "Erreur : {msg}",
      pw_mismatch: "Les deux mots de passe ne correspondent pas.",
      server_unreachable: "Impossible de joindre le serveur."
    },
    en: {
      invoice_created: "Invoice {number} generated successfully!",
      user_created: "User \"{email}\" registered successfully!",
      client_saved: "Customer \"{name}\" saved successfully!",
      payment_saved: "Payment recorded: the invoice is marked as paid.",
      payment_success: "Payment received. The invoice will be marked “Paid” once the provider confirms.",
      payment_cancel: "Payment cancelled. The invoice remains pending.",
      error_prefix: "Error: {msg}",
      pw_mismatch: "The two passwords do not match.",
      server_unreachable: "Unable to reach the server."
    },
    ar: {
      invoice_created: "تم إنشاء الفاتورة {number} بنجاح!",
      user_created: "تم تسجيل المستخدم \"{email}\" بنجاح!",
      client_saved: "تم حفظ العميل \"{name}\" بنجاح!",
      payment_saved: "تم تسجيل الدفعة: الفاتورة مسددة.",
      payment_success: "تم استلام الدفعة. ستصبح الفاتورة «مسددة» بعد تأكيد مزوّد الدفع.",
      payment_cancel: "تم إلغاء الدفع. تبقى الفاتورة قيد الانتظار.",
      error_prefix: "خطأ: {msg}",
      pw_mismatch: "كلمتا المرور غير متطابقتين.",
      server_unreachable: "تعذّر الاتصال بالخادم."
    }
  };

  /* ---------- Index de recherche ---------- */
  const norm = s => String(s).replace(/\s+/g, ' ').trim();
  const IDX = { en: new Map(), ar: new Map() };
  const FR_SET = new Set();
  PHRASES.forEach(([fr, en, ar]) => {
    const k = norm(fr);
    FR_SET.add(k);
    IDX.en.set(k, en);
    IDX.ar.set(k, ar);
  });

  let currentLang = 'fr';
  const missing = new Set();

  function translatePhrase(fr, lang) {
    if (lang === 'fr') return fr;
    const k = norm(fr);
    const hit = IDX[lang] && IDX[lang].get(k);
    if (hit === undefined) {
      if (/[A-Za-zÀ-ÿ]{3,}/.test(k)) missing.add(k);
      return null;
    }
    return hit;
  }

  /* ---------- API publique : t() ---------- */
  function t(key, params) {
    let s = (MESSAGES[currentLang] && MESSAGES[currentLang][key]) ||
            MESSAGES.fr[key];
    if (s === undefined) {
      const tr = translatePhrase(key, currentLang);
      s = tr !== null ? tr : key;
    }
    if (params) Object.keys(params).forEach(p => { s = s.replace(new RegExp('\\{' + p + '\\}', 'g'), params[p]); });
    return s;
  }

  /* ---------- Traduction du DOM ---------- */
  const textState = new WeakMap(); // Text node -> {fr, shown}
  const attrState = new WeakMap(); // Element   -> {attr: {fr, shown}}
  const ATTRS = ['placeholder', 'title', 'alt', 'aria-label', 'label'];
  const SKIP = new Set(['SCRIPT', 'STYLE', 'TEXTAREA', 'CODE', 'PRE', 'NOSCRIPT']);

  function translateTextNode(node, lang) {
    const raw = node.nodeValue;
    if (!raw || !raw.trim()) return;
    let st = textState.get(node);
    if (!st || st.shown !== raw) st = { fr: raw, shown: raw }; // contenu nouveau (ou modifié par le JS)
    const lead = st.fr.match(/^\s*/)[0];
    const trail = st.fr.match(/\s*$/)[0];
    let out = st.fr;
    if (lang !== 'fr') {
      const tr = translatePhrase(st.fr, lang);
      if (tr !== null) out = lead + tr + trail;
    }
    if (out !== raw) node.nodeValue = out;
    st.shown = out;
    textState.set(node, st);
  }

  function translateAttrs(el, lang) {
    let states = attrState.get(el);
    ATTRS.forEach(attr => {
      if (!el.hasAttribute(attr)) return;
      const cur = el.getAttribute(attr);
      if (!cur || !cur.trim()) return;
      states = states || {};
      let st = states[attr];
      if (!st || st.shown !== cur) st = { fr: cur, shown: cur };
      let out = st.fr;
      if (lang !== 'fr') {
        const tr = translatePhrase(st.fr, lang);
        if (tr !== null) out = tr;
      }
      if (out !== cur) el.setAttribute(attr, out);
      st.shown = out;
      states[attr] = st;
    });
    if (states) attrState.set(el, states);
  }

  function translateTree(root, lang) {
    if (!root) return;
    if (root.nodeType === Node.TEXT_NODE) { translateTextNode(root, lang); return; }
    if (root.nodeType !== Node.ELEMENT_NODE || SKIP.has(root.tagName) || root.closest('[data-no-i18n]')) return;
    translateAttrs(root, lang);
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT, {
      acceptNode(n) {
        if (n.nodeType === Node.ELEMENT_NODE) {
          return (SKIP.has(n.tagName) || n.hasAttribute('data-no-i18n')) ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT;
        }
        return NodeFilter.FILTER_ACCEPT;
      }
    });
    let n;
    while ((n = walker.nextNode())) {
      if (n.nodeType === Node.TEXT_NODE) translateTextNode(n, lang);
      else translateAttrs(n, lang);
    }
  }

  const titleState = { fr: null, shown: null };
  function translateTitle(lang) {
    if (titleState.fr === null || titleState.shown !== document.title) {
      titleState.fr = document.title;
    }
    let out = titleState.fr;
    if (lang !== 'fr') {
      out = titleState.fr.split(' — ').map(p => translatePhrase(p, lang) || p).join(' — ');
    }
    document.title = out;
    titleState.shown = out;
  }

  /* ---------- Observation du contenu dynamique ---------- */
  let observer = null, pending = new Set(), scheduled = false;
  function flush() {
    scheduled = false;
    observer && observer.disconnect();
    pending.forEach(n => { if (n.isConnected || n.nodeType === Node.TEXT_NODE) translateTree(n, currentLang); });
    pending.clear();
    startObserver();
  }
  function startObserver() {
    if (!observer) {
      observer = new MutationObserver(muts => {
        muts.forEach(m => {
          if (m.type === 'characterData') pending.add(m.target);
          m.addedNodes.forEach(n => pending.add(n));
        });
        if (!scheduled) { scheduled = true; requestAnimationFrame(flush); }
      });
    }
    observer.observe(document.body, { childList: true, subtree: true, characterData: true });
  }

  /* ---------- Utilisateur connecté (topbar) ---------- */
  function updateCurrentUserDisplay() {
    let user = null;
    const json = localStorage.getItem('current_user') || localStorage.getItem('demo_user');
    if (json) { try { user = JSON.parse(json); } catch (e) {} }
    const displayName = user?.username || (user?.email ? user.email.split('@')[0] : 'Admin');
    document.querySelectorAll('.user-info span, #user-display-name').forEach(el => {
      el.textContent = displayName;
      el.setAttribute('data-no-i18n', '');
    });
    document.querySelectorAll('.user-info img, #user-avatar').forEach(img => {
      img.src = `https://ui-avatars.com/api/?name=${encodeURIComponent(displayName)}&background=1a73e8&color=fff&bold=true`;
      img.alt = displayName;
    });
  }

  /* ---------- Changement de langue ---------- */
  function applyLanguage(lang) {
    if (!LANGS[lang]) lang = 'fr';
    currentLang = lang;
    localStorage.setItem('nexa_lang', lang);

    const html = document.documentElement;
    html.setAttribute('lang', lang);
    html.setAttribute('dir', LANGS[lang].dir);

    observer && observer.disconnect();
    translateTree(document.body, lang);
    translateTitle(lang);
    startObserver();

    const sel = document.getElementById('lang-select');
    if (sel && sel.value !== lang) sel.value = lang;

    document.dispatchEvent(new CustomEvent('langchange', { detail: { lang } }));
  }

  /* ---------- Sélecteur de langue ---------- */
  function initLanguageSelector() {
    if (document.getElementById('lang-select')) return;
    const wrapper = document.createElement('div');
    wrapper.className = 'lang-selector-wrapper';
    wrapper.setAttribute('data-no-i18n', '');
    wrapper.innerHTML = `
      <select id="lang-select" aria-label="Language" style="background:#f8fafc;border:1px solid #cbd5e1;border-radius:6px;padding:6px 8px;font-size:13px;font-weight:600;color:#334155;cursor:pointer;outline:none;">
        ${Object.keys(LANGS).map(l => `<option value="${l}">${LANGS[l].label}</option>`).join('')}
      </select>`;

    const bar = document.querySelector('.topbar-right');
    if (bar) {
      wrapper.style.cssText = 'display:inline-flex;align-items:center;margin-inline-end:4px;';
      const userInfo = bar.querySelector('.user-info');
      userInfo ? bar.insertBefore(wrapper, userInfo) : bar.appendChild(wrapper);
    } else {
      // Pages sans topbar (connexion, inscription) : sélecteur flottant
      wrapper.style.cssText = 'position:fixed;top:14px;inset-inline-end:14px;z-index:2000;';
      document.body.appendChild(wrapper);
    }
    wrapper.querySelector('select').addEventListener('change', e => applyLanguage(e.target.value));
  }

  /* ---------- Formatage selon la langue ---------- */
  const locale = () => LANGS[currentLang].locale;
  const fmtNumber = (n, o) => Number(n || 0).toLocaleString(locale(), o || { minimumFractionDigits: 2 });
  const fmtMoney  = (n, cur) => fmtNumber(n) + ' ' + (cur || '€');
  const fmtDate   = (d, o) => new Date(d).toLocaleDateString(locale(), o || { day: '2-digit', month: 'long', year: 'numeric' });

  window.i18n = {
    t, applyLanguage, setLang: applyLanguage,
    getLang: () => currentLang,
    locale, fmtNumber, fmtMoney, fmtDate,
    missing: () => { console.table([...missing].map(p => ({ 'À traduire (FR)': p }))); return [...missing]; }
  };
  window.applyLanguage = applyLanguage;      // compatibilité
  window.t = window.t || t;

  document.addEventListener('DOMContentLoaded', () => {
    updateCurrentUserDisplay();
    initLanguageSelector();
    applyLanguage(localStorage.getItem('nexa_lang') || 'fr');
  });
})();