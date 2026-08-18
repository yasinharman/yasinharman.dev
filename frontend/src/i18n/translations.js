/**
 * Sitedeki tüm metinler. Yeni bir metin eklerken iki dile de eklemeyin unutmayın:
 * eksik anahtar, o dilde `undefined` olarak render edilir.
 *
 * Not: Sohbet cevaplarının dili buradan gelmez — o, /chat isteğine giden
 * `lang` alanıyla backend tarafında belirlenir (bkz. HomePage.jsx).
 */
export const LANGUAGES = ['tr', 'en'];
export const DEFAULT_LANGUAGE = 'tr';

export const translations = {
  tr: {
    documentTitle: 'YasinHarman | Yapay Zeka Asistanı',

    languageSwitch: {
      label: 'Dil seçimi',
      tr: 'TUR',
      en: 'EN',
    },

    nav: {
      home: 'Anasayfa',
      experience: 'İş Tecrübelerim',
      projects: 'Projelerim',
      backHome: 'Anasayfaya dön',
    },

    hero: {
      // Vurgulu "Yasin" kelimesinin cümledeki yeri dile göre değişir:
      // TR'de başta, EN'de sonda. Bu yüzden başlık üç parçaya bölündü.
      titleBefore: '',
      titleName: 'Yasin',
      titleAfter: ' hakkında ne bilmek istersiniz?',
      subtitle: 'Merhaba, ben Jarvis! Yasin hakkındaki soruları yanıtlamak için eğitildim.',
      placeholders: [
        "Yasin '...' rolünde görev alabilir mi?",
        "Yasin'in iletişim bilgileri neler?",
        "Yasin'in projelerinden bahsedebilir misin?",
        "Yasin'in kullanabildiği teknolojiler neler?",
        'Yasin hangi sosyal etkinliklere katıldı?',
      ],
    },

    chat: {
      assistantName: 'Jarvis',
      assistantRole: 'YasinHarman için Yapay Zeka Asistanı',
      inputPlaceholder: 'Başka bir soru sorun...',
      footer: 'Jarvis, bilgiyi sentezlemek için FastAPI + LangChain kullanır',
      errorPrefix: 'Hata',
    },

    experience: {
      heading: 'İŞ TECRÜBELERİM',
      technologies: 'Teknolojiler',
      viewProfile: 'Profili Görüntüle',
    },

    projects: {
      heading: 'PROJELERİM',
      technologies: 'Teknolojiler',
      showDetails: 'Detayları Göster',
      hideDetails: 'Detayları Gizle',
      detailsComingSoon: 'Detaylar Hazırlanıyor',
      viewOnGithub: "GitHub'da Görüntüle",
    },
  },

  en: {
    documentTitle: 'YasinHarman | AI Assistant',

    languageSwitch: {
      label: 'Language selection',
      tr: 'TUR',
      en: 'EN',
    },

    nav: {
      home: 'Home',
      experience: 'My Experience',
      projects: 'My Projects',
      backHome: 'Back to home',
    },

    hero: {
      titleBefore: 'What would you like to know about ',
      titleName: 'Yasin',
      titleAfter: '?',
      subtitle: "Hi, I'm Jarvis! I was trained to answer questions about Yasin.",
      placeholders: [
        "Would Yasin be a fit for the '...' role?",
        "What are Yasin's contact details?",
        "Can you tell me about Yasin's projects?",
        'Which technologies can Yasin work with?',
        'Which community events has Yasin taken part in?',
      ],
    },

    chat: {
      assistantName: 'Jarvis',
      assistantRole: 'AI Assistant for YasinHarman',
      inputPlaceholder: 'Ask another question...',
      footer: 'Jarvis uses FastAPI + LangChain to synthesise information',
      errorPrefix: 'Error',
    },

    experience: {
      heading: 'MY EXPERIENCE',
      technologies: 'Technologies',
      viewProfile: 'View Profile',
    },

    projects: {
      heading: 'MY PROJECTS',
      technologies: 'Technologies',
      showDetails: 'Show Details',
      hideDetails: 'Hide Details',
      detailsComingSoon: 'Details Coming Soon',
      viewOnGithub: 'View on GitHub',
    },
  },
};
