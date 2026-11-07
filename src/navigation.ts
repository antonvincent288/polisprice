import { getPermalink } from './utils/permalinks';

export const headerData = {
  links: [
    { text: 'Калькулятор', href: getPermalink('/osago/kalkulyator/') },
    { text: 'Коэффициенты', href: getPermalink('/osago/koeffitsienty/') },
    { text: 'Тарифы', href: getPermalink('/osago/tarify/') },
    { text: 'Все регионы', href: getPermalink('/osago/regiony/') },
    { text: 'ОСАГО в Москве', href: getPermalink('/osago/moscow/') },
    { text: 'Модели авто', href: getPermalink('/osago/na-avtomobili/') },
    { text: 'Гайды', href: getPermalink('/guides/') },
  ],
  actions: [{ text: 'Рассчитать ОСАГО', href: getPermalink('/osago/kalkulyator/'), variant: 'primary' }],
};

export const footerData = {
  links: [
    { title: 'Инструменты', links: [
      { text: 'Калькулятор ОСАГО', href: getPermalink('/osago/kalkulyator/') },
      { text: 'Справочник коэффициентов', href: getPermalink('/osago/koeffitsienty/') },
      { text: 'Тарифы 2026', href: getPermalink('/osago/tarify/') },
      { text: 'Изменения 2026', href: getPermalink('/osago/izmeneniya-2026/') },
    ]},
    { title: 'Гайды', links: [
      { text: 'КБМ после смены фамилии', href: getPermalink('/guides/kbm-posle-smeny-famili/') },
      { text: 'Проверка полиса на подлинность', href: getPermalink('/guides/proverka-polisa-osago/') },
      { text: 'Штраф за отсутствие ОСАГО', href: getPermalink('/guides/shtraf-za-osago/') },
      { text: 'Все гайды', href: getPermalink('/guides/') },
    ]},
    { title: 'Информация', links: [
      { text: 'О проекте', href: getPermalink('/o-proekte/') },
      { text: 'Контакты', href: getPermalink('/kontakty/') },
      { text: 'Оферта', href: getPermalink('/oferta/') },
      { text: 'Политика конфиденциальности', href: getPermalink('/politika-konfidencialnosti/') },
    ]},
  ],
  secondaryLinks: [],
  socialLinks: [],
  footNote: `Расчёты по Указанию Банка России от 09.10.2025 № 7204-У (ред. от 04.05.2026). ПолисПрайс — справочник тарифов и коэффициентов: не является страховой компанией и не продаёт полисы.`,
};

