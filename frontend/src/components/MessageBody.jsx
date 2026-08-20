import { Fragment } from 'react';

/**
 * Model cevapları markdown olarak geliyor (bkz. backend/app/agent.py > Biçim Sözleşmesi).
 * Burada satırları bloklara ayırıp her seviyeye ayrı bir görsel dil veriyoruz:
 * başlık + etiket pill'leri, madde, paragraf. Biçim kapalı bir küme olduğu için
 * markdown kütüphanesi yerine ~40 satırlık parser yetiyor.
 */

const HEADING_RE = /^#{1,6}\s+(.*)$/;
const BULLET_RE = /^(?:[-*•]|\d+[.)])\s+(.*)$/;
const BOLD_ONLY_RE = /^\*\*(.+?)\*\*[\s.:]*$/;
const META_LINE_RE = /^[(（]([^()]+)[)）]$/;
const META_SPLIT_RE = /\s*[,;·|]\s*/;

// Satır içinde ayrıca çizilen şeyler: link, e-posta, telefon, **kalın**, `kod`, tutar.
// Korpustaki adresler protokolsüz yazılı (linkedin.com/in/...), o yüzden çıplak alan
// adlarını da yakalıyoruz; TLD listesi bilerek dar, "Node.js" gibi isimlere takılmasın.
const INLINE_PATTERNS = [
  String.raw`\[[^\]\n]+\]\([^)\s]+\)`,                                        // [etiket](hedef)
  String.raw`\*\*[^*]+\*\*`,                                                   // **kalın**
  '`[^`]+`',                                                                   // `kod`
  String.raw`https?:\/\/\S+`,                                                  // tam URL
  String.raw`[\w.+-]+@[\w-]+(?:\.[\w-]+)+`,                                     // e-posta
  String.raw`(?:www\.)?[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9-]+)*\.(?:com|dev|net|org|io|ai|app|tr)(?:\/\S*)?`,
  String.raw`(?:\+90|0)[\s-]?\(?\d{3}\)?[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}`,    // telefon
  String.raw`[$₺€]\s?\d[\d.,]*\+?|\d[\d.,]*\+?\s?[$₺€]|%\d+(?:[.,]\d+)?`,        // tutar / yüzde
];
const INLINE_RE = new RegExp(`(${INLINE_PATTERNS.join('|')})`, 'gi');

const MD_LINK_RE = /^\[([^\]\n]+)\]\(([^)\s]+)\)$/;
const EMAIL_RE = /^[\w.+-]+@[\w-]+(?:\.[\w-]+)+$/;
const PHONE_RE = /^(?:\+90|0)[\s-]?\(?\d{3}\)?[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}$/;
const DOMAIN_RE = /^(?:www\.)?[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9-]+)*\.[a-z]{2,}(?:\/\S*)?$/i;
// "yasinharman.dev." — cümle sonundaki noktalama linkin parçası değildir.
const TRAILING_PUNCT_RE = /[.,;:!?)\]}'"»…]+$/;

// href'ler LLM çıktısından geliyor; yalnızca bu üç şemaya izin ver, gerisini düz metne düşür.
function hrefFor(target) {
  if (/^(?:https?:\/\/|mailto:|tel:)/i.test(target)) return target;
  if (EMAIL_RE.test(target)) return `mailto:${target}`;
  if (PHONE_RE.test(target)) return `tel:${target.replace(/[^\d+]/g, '').replace(/^0/, '+90')}`;
  if (DOMAIN_RE.test(target)) return `https://${target}`;
  return null;
}

function Link({ href, children }) {
  const isExternal = /^https?:/i.test(href);
  return (
    <a
      href={href}
      target={isExternal ? '_blank' : undefined}
      rel={isExternal ? 'noopener noreferrer' : undefined}
      className="font-medium text-orange-300 underline decoration-orange-400/40 underline-offset-2 transition-colors hover:text-orange-200 hover:decoration-orange-300"
    >
      {children}
    </a>
  );
}

const splitMeta = (text) => text.split(META_SPLIT_RE).map((part) => part.trim()).filter(Boolean);

// "MegaGear — Software Engineer (Tam Zamanlı, Mayıs 2026 – Temmuz 2026)"
// -> title + ["Tam Zamanlı", "Mayıs 2026 – Temmuz 2026"]
function splitHeading(text) {
  const match = text.match(/^(.*?)\s*[(（]([^()]*)[)）][\s.:]*$/);
  if (!match || !match[1].trim()) return { title: text.trim(), meta: [] };
  return { title: match[1].trim(), meta: splitMeta(match[2]) };
}

/** Ham cevabı {heading | bullet | para} bloklarına çevirir. */
export function parseAnswer(content) {
  const lines = String(content).replace(/\r\n/g, '\n').split('\n');
  const blocks = [];

  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (!line) continue;

    const indent = rawLine.match(/^[ \t]*/)[0].replace(/\t/g, '  ').length;
    const previous = blocks[blocks.length - 1];

    const heading = line.match(HEADING_RE);
    if (heading) {
      blocks.push({ type: 'heading', ...splitHeading(heading[1]) });
      continue;
    }

    const bullet = line.match(BULLET_RE);
    if (bullet) {
      const body = bullet[1].trim();
      const bold = body.match(BOLD_ONLY_RE);
      // Yalnızca kalın metinden oluşan üst seviye madde başlıktır — modelin
      // sözleşme öncesi ürettiği "- **Şirket — Rol**" biçimi de böyle yakalanır.
      if (bold && indent < 2) blocks.push({ type: 'heading', ...splitHeading(bold[1]) });
      else blocks.push({ type: 'bullet', text: body, indent });
      continue;
    }

    const bold = line.match(BOLD_ONLY_RE);
    if (bold) {
      blocks.push({ type: 'heading', ...splitHeading(bold[1]) });
      continue;
    }

    // Başlığın altına ayrı satıra yazılmış "( Freelance · 2025 – Günümüz )" etiketleri.
    const metaLine = line.match(META_LINE_RE);
    if (metaLine && previous?.type === 'heading') {
      previous.meta = previous.meta.concat(splitMeta(metaLine[1]));
      continue;
    }

    blocks.push({ type: 'para', text: line });
  }

  // Girinti mutlak değil göreli: en dıştaki madde her zaman 0. seviye sayılır.
  const indents = blocks.filter((block) => block.type === 'bullet').map((block) => block.indent);
  const base = indents.length ? Math.min(...indents) : 0;
  return blocks.map((block) =>
    block.type === 'bullet'
      ? { type: 'bullet', text: block.text, depth: block.indent - base >= 2 ? 1 : 0 }
      : block,
  );
}

/** Balonun geniş mi yoksa dar mı çizileceğine karar vermek için ucuz kontrol. */
export function isStructuredAnswer(content) {
  return /^\s*(?:[-*•]|\d+[.)]|#{1,6}|\*\*)\s*\S/m.test(String(content));
}

function renderInline(text) {
  return text.split(INLINE_RE).filter(Boolean).map((token, index) => {
    if (token.startsWith('**') && token.endsWith('**')) {
      return <strong key={index} className="font-semibold text-white">{token.slice(2, -2)}</strong>;
    }
    if (token.startsWith('`') && token.endsWith('`')) {
      return (
        <code
          key={index}
          className="mx-0.5 rounded border border-white/10 bg-zinc-900/60 px-1.5 py-0.5 font-mono text-[13px] text-orange-200"
        >
          {token.slice(1, -1)}
        </code>
      );
    }
    const mdLink = token.match(MD_LINK_RE);
    if (mdLink) {
      const href = hrefFor(mdLink[2]);
      return href ? (
        <Link key={index} href={href}>{mdLink[1]}</Link>
      ) : (
        <Fragment key={index}>{mdLink[1]}</Fragment>
      );
    }

    const trailing = token.match(TRAILING_PUNCT_RE)?.[0] ?? '';
    const target = trailing ? token.slice(0, -trailing.length) : token;
    const href = hrefFor(target);
    if (href) {
      return (
        <Fragment key={index}>
          <Link href={href}>{target}</Link>
          {trailing}
        </Fragment>
      );
    }

    if (/\d/.test(token) && /[$₺€%]/.test(token)) {
      return <span key={index} className="font-semibold text-orange-300">{token}</span>;
    }
    return <Fragment key={index}>{token}</Fragment>;
  });
}

export function MessageBody({ content }) {
  const blocks = parseAnswer(content);

  if (!blocks.some((block) => block.type === 'heading' || block.type === 'bullet')) {
    return <span className="whitespace-pre-wrap break-words">{renderInline(String(content).trim())}</span>;
  }

  return (
    <div className="space-y-2.5 break-words">
      {blocks.map((block, index) => {
        // Bloklar sırayla açılır: cevap tek seferde geliyor ama "kuruluyor" gibi görünür.
        const style = { animationDelay: `${Math.min(index * 60, 480)}ms`, animationFillMode: 'both' };

        if (block.type === 'heading') {
          return (
            <div
              key={index}
              style={style}
              className={`animate-slide-up ${index > 0 ? 'mt-5 border-t border-white/10 pt-4' : ''}`}
            >
              <h4 className="border-l-2 border-orange-500 pl-3 text-[15px] font-semibold leading-snug text-white">
                {renderInline(block.title)}
              </h4>
              {block.meta.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1.5 pl-3">
                  {block.meta.map((item) => (
                    <span
                      key={item}
                      className="rounded-full border border-orange-500/25 bg-orange-500/10 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider text-orange-200/90"
                    >
                      {item}
                    </span>
                  ))}
                </div>
              )}
            </div>
          );
        }

        if (block.type === 'bullet') {
          return (
            <div
              key={index}
              style={style}
              className={`animate-slide-up flex gap-2.5 ${block.depth ? 'pl-8' : 'pl-3'}`}
            >
              <span
                aria-hidden="true"
                className={`mt-[8px] shrink-0 ${
                  block.depth ? 'h-1 w-1 rounded-full bg-orange-500/40' : 'h-1.5 w-1.5 rotate-45 bg-orange-500/70'
                }`}
              />
              <p className="flex-1 text-[15px] leading-relaxed text-orange-50/85">{renderInline(block.text)}</p>
            </div>
          );
        }

        return (
          <p key={index} style={style} className="animate-slide-up text-[15px] leading-relaxed text-orange-50/85">
            {renderInline(block.text)}
          </p>
        );
      })}
    </div>
  );
}
