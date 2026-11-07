import guides from '~/data/guides.json';

const esc = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

export async function GET(context) {
  const items = guides
    .map((g) => {
      const link = `https://polisprice.ru/guides/${g.slug}/`;
      return `<item><title>${esc(g.title)}</title><link>${link}</link><guid>${link}</guid><pubDate>${new Date(g.dateModified).toUTCString()}</pubDate><description>${esc(g.desc)}</description></item>`;
    })
    .join('');
  const xml = `<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>ПолисПрайс — гайды по ОСАГО</title><link>https://polisprice.ru/</link><description>Расчёт ОСАГО по коэффициентам ЦБ: КТ, КБМ, КВС, КМ, КО, КС</description><language>ru</language>${items}</channel></rss>`;
  return new Response(xml, { headers: { 'Content-Type': 'application/xml; charset=utf-8' } });
}
