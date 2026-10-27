/* Brand art: logo and hand-drawn vegetable illustrations (original SVG). */
const LOGO_INNER = `
  <path d="M25.6 43.9A38 38 0 0 1 86.9 33.1" fill="none" stroke="#C9E265" stroke-width="9" stroke-linecap="round"/>
  <path d="M94.8 25.2L96.4 42.7L78.9 41.1Z" fill="#C9E265" stroke="#C9E265" stroke-width="3" stroke-linejoin="round"/>
  <path d="M94.4 76.1A38 38 0 0 1 33.1 86.9" fill="none" stroke="#F4B93A" stroke-width="9" stroke-linecap="round"/>
  <path d="M25.2 94.8L23.6 77.3L41.1 78.9Z" fill="#F4B93A" stroke="#F4B93A" stroke-width="3" stroke-linejoin="round"/>
  <path d="M60 31C80 41 82 68 60 90C38 68 40 41 60 31Z" fill="#fff"/>
  <path d="M60 31C80 41 82 68 60 90C60 70 60 50 60 31Z" fill="#E4F2C4"/>
  <path d="M60 40V84" stroke="#2F9E4F" stroke-width="3" stroke-linecap="round"/>
  <path d="M60 58L50 50M60 68L49 60M60 58L70 50M60 68L71 60" stroke="#2F9E4F" stroke-width="2.4" stroke-linecap="round"/>`;

function logoSVG(size = 96, tile = true) {
  const bg = tile
    ? `<rect width="120" height="120" rx="28" fill="#0F3D2E"/>`
    : "";
  return `<svg viewBox="0 0 120 120" width="${size}" height="${size}" role="img" aria-label="FoodLoop">${bg}${LOGO_INNER}</svg>`;
}

const VEG = {
  tomato: `
    <ellipse cx="50" cy="58" rx="36" ry="31" fill="#E8472F"/>
    <path d="M18 62C22 84 44 92 64 88C48 82 30 78 18 62Z" fill="#B8301D" opacity=".28"/>
    <ellipse cx="34" cy="46" rx="9" ry="6" fill="#fff" opacity=".32" transform="rotate(-30 34 46)"/>
    <path d="M50 30L41 22L47 31L36 28L45 35L40 40L50 36L60 40L55 35L64 28L53 31L59 22Z" fill="#2F9E4F"/>
    <path d="M50 30V18" stroke="#1F7A3A" stroke-width="5" stroke-linecap="round"/>`,
  carrot: `
    <path d="M26 38C40 28 62 30 74 42L56 90C54 96 48 96 46 90Z" fill="#F28C28" transform="rotate(28 50 62)"/>
    <g transform="rotate(28 50 62)" stroke="#C86A12" stroke-width="2.4" stroke-linecap="round" opacity=".55">
      <path d="M38 48H50M44 60H58M48 72H56"/></g>
    <g transform="rotate(28 50 62)">
      <path d="M50 34C42 24 36 14 40 6C48 12 52 22 50 34Z" fill="#2F9E4F"/>
      <path d="M50 34C54 22 62 14 70 14C66 24 58 32 50 34Z" fill="#43B25F"/>
      <path d="M50 34C46 24 50 12 56 4C60 14 56 26 50 34Z" fill="#1F7A3A"/></g>`,
  broccoli: `
    <path d="M42 94L38 62H62L58 94Z" fill="#8FCB6B"/>
    <path d="M50 64V90" stroke="#6FAE4D" stroke-width="3" stroke-linecap="round"/>
    <circle cx="30" cy="48" r="16" fill="#2F8F46"/><circle cx="50" cy="36" r="19" fill="#2F8F46"/>
    <circle cx="70" cy="48" r="16" fill="#2F8F46"/><circle cx="50" cy="54" r="15" fill="#277A3B"/>
    <circle cx="42" cy="30" r="5" fill="#4FB063" opacity=".8"/><circle cx="60" cy="40" r="4" fill="#4FB063" opacity=".8"/>
    <circle cx="26" cy="44" r="4" fill="#4FB063" opacity=".8"/><circle cx="70" cy="44" r="4" fill="#4FB063" opacity=".7"/>`,
  eggplant: `
    <path d="M34 28C22 44 14 74 32 88C48 98 72 88 76 64C78 48 70 34 58 28C50 24 42 24 34 28Z" fill="#5B2A6B" transform="rotate(-18 50 60)"/>
    <ellipse cx="38" cy="58" rx="6" ry="14" fill="#fff" opacity=".18" transform="rotate(-18 38 58)"/>
    <g transform="rotate(-18 50 60)"><path d="M26 30C32 22 44 18 56 22C62 24 66 28 64 34C56 30 40 30 26 30Z" fill="#2F9E4F"/>
    <path d="M44 24L42 10" stroke="#1F7A3A" stroke-width="5" stroke-linecap="round"/></g>`,
  chilli: `
    <path d="M30 24C46 22 74 30 80 58C84 76 70 90 56 94C70 80 64 56 44 46C36 42 28 36 30 24Z" fill="#D7261E"/>
    <path d="M44 40C58 44 70 56 70 70" stroke="#fff" stroke-width="3" stroke-linecap="round" opacity=".28" fill="none"/>
    <path d="M30 24C26 18 28 12 36 10C34 16 38 20 44 22Z" fill="#2F9E4F"/>
    <path d="M36 10C34 6 38 2 44 4" stroke="#1F7A3A" stroke-width="4" stroke-linecap="round" fill="none"/>`,
  capsicum: `
    <path d="M26 40C26 30 38 26 50 32C62 26 74 30 74 40C80 60 72 88 56 90C52 90 48 90 44 90C28 88 20 60 26 40Z" fill="#F4B93A"/>
    <path d="M50 32C46 50 46 72 50 90" stroke="#D99A1C" stroke-width="3" fill="none" opacity=".6"/>
    <path d="M38 36C34 52 34 72 40 86" stroke="#D99A1C" stroke-width="2.5" fill="none" opacity=".45"/>
    <ellipse cx="36" cy="46" rx="4" ry="9" fill="#fff" opacity=".35"/>
    <path d="M50 32V18" stroke="#2F9E4F" stroke-width="6" stroke-linecap="round"/>
    <path d="M38 30C44 24 56 24 62 30C58 34 42 34 38 30Z" fill="#2F9E4F"/>`,
  greens: `
    <path d="M50 94C44 70 18 62 14 32C34 30 50 48 50 70C50 48 66 30 86 32C82 62 56 70 50 94Z" fill="#43B25F"/>
    <path d="M50 94V30" stroke="#1F7A3A" stroke-width="3.5" stroke-linecap="round"/>
    <path d="M50 70L30 50M50 58L68 44M50 80L68 68M50 76L34 64" stroke="#1F7A3A" stroke-width="2.4" stroke-linecap="round" opacity=".7"/>
    <path d="M50 30C40 22 40 10 50 4C60 10 60 22 50 30Z" fill="#6FCB7F"/>`,
  onion: `
    <path d="M50 22C70 38 88 52 82 70C76 88 60 94 50 94C40 94 24 88 18 70C12 52 30 38 50 22Z" fill="#9B4FA3"/>
    <path d="M50 22C42 44 40 72 50 94M50 22C58 44 60 72 50 94" stroke="#7A3585" stroke-width="2.4" fill="none" opacity=".7"/>
    <ellipse cx="34" cy="62" rx="5" ry="12" fill="#fff" opacity=".25"/>
    <path d="M50 22C46 14 50 8 56 6C54 12 54 16 50 22Z" fill="#C9A66B"/>
    <path d="M50 94C44 96 40 98 36 98M50 94C56 96 60 98 64 98" stroke="#C9A66B" stroke-width="2.4" stroke-linecap="round"/>`,
  corn: `
    <path d="M50 8C66 18 72 46 66 70C62 84 56 92 50 94C44 92 38 84 34 70C28 46 34 18 50 8Z" fill="#F4C63A"/>
    <g fill="#D99A1C" opacity=".5"><circle cx="44" cy="30" r="2.5"/><circle cx="54" cy="30" r="2.5"/>
    <circle cx="40" cy="42" r="2.5"/><circle cx="50" cy="42" r="2.5"/><circle cx="60" cy="42" r="2.5"/>
    <circle cx="38" cy="54" r="2.5"/><circle cx="48" cy="54" r="2.5"/><circle cx="58" cy="54" r="2.5"/>
    <circle cx="42" cy="66" r="2.5"/><circle cx="52" cy="66" r="2.5"/><circle cx="62" cy="66" r="2.5"/></g>
    <path d="M50 94C26 88 16 62 24 36C32 56 40 72 50 94Z" fill="#43B25F"/>
    <path d="M50 94C74 88 84 62 76 36C68 56 60 72 50 94Z" fill="#2F9E4F"/>`,
  pumpkin: `
    <ellipse cx="50" cy="60" rx="38" ry="30" fill="#F28C28"/>
    <path d="M50 30C40 40 38 78 50 90M50 30C60 40 62 78 50 90" stroke="#C86A12" stroke-width="3" fill="none" opacity=".55"/>
    <path d="M30 34C22 44 22 76 34 86M70 34C78 44 78 76 66 86" stroke="#C86A12" stroke-width="2.5" fill="none" opacity=".4"/>
    <ellipse cx="30" cy="52" rx="5" ry="9" fill="#fff" opacity=".22"/>
    <path d="M50 32V20" stroke="#6B8E23" stroke-width="7" stroke-linecap="round"/>`,
};


/* Category pictures for the "Add a lot" screen (original SVG, same style as above). */
const wheatEar = (x, rot) => `<g transform="translate(${x} 0) rotate(${rot} 50 92)">
  <path d="M50 92V34" stroke="#B8862B" stroke-width="3" stroke-linecap="round"/>
  ${[0, 1, 2, 3, 4].map((i) => `<ellipse cx="43" cy="${38 + i * 9}" rx="4.2" ry="7" fill="#E9B94A" transform="rotate(-24 43 ${38 + i * 9})"/>
  <ellipse cx="57" cy="${38 + i * 9}" rx="4.2" ry="7" fill="#F4C85C" transform="rotate(24 57 ${38 + i * 9})"/>`).join("")}
  <ellipse cx="50" cy="26" rx="4" ry="8" fill="#E9B94A"/></g>`;
Object.assign(VEG, {
  cat_vegetables: `
    <g transform="translate(20 2) scale(.8)">${VEG.carrot}</g>
    <g transform="translate(-8 8) scale(.84)">${VEG.broccoli}</g>
    <g transform="translate(48 52) scale(.42)">${VEG.tomato}</g>`,
  cat_fruits: `
    <circle cx="70" cy="62" r="21" fill="#F28C28"/><ellipse cx="62" cy="54" rx="6" ry="4" fill="#fff" opacity=".3" transform="rotate(-30 62 54)"/>
    <path d="M70 41C72 36 78 34 82 36C80 41 75 43 70 41Z" fill="#2F9E4F"/>
    <path d="M36 40C22 36 12 48 14 62C16 78 30 88 40 84C48 88 62 82 62 64C62 48 50 36 36 40Z" fill="#E8472F"/>
    <path d="M18 64C22 78 34 84 40 80C30 78 22 72 18 64Z" fill="#B8301D" opacity=".3"/>
    <ellipse cx="26" cy="52" rx="5" ry="3.4" fill="#fff" opacity=".35" transform="rotate(-35 26 52)"/>
    <path d="M38 42V28" stroke="#6B4423" stroke-width="3.4" stroke-linecap="round"/>
    <path d="M38 32C44 22 54 22 58 26C54 34 44 36 38 32Z" fill="#2F9E4F"/>`,
  cat_dairy: `
    <path d="M52 52L90 60V86H52Z" fill="#F4C85C"/><path d="M52 52L90 60L72 46Z" fill="#FADB86"/>
    <circle cx="66" cy="70" r="3.4" fill="#D9A22B"/><circle cx="80" cy="76" r="2.6" fill="#D9A22B"/><circle cx="72" cy="80" r="2" fill="#D9A22B"/>
    <rect x="30" y="12" width="22" height="9" rx="3" fill="#4A90D9"/>
    <path d="M32 21H50V32C62 38 66 46 66 58V84C66 90 62 94 56 94H26C20 94 16 90 16 84V58C16 46 20 38 32 32Z" fill="#fff" stroke="#C9D8E8" stroke-width="2.4"/>
    <rect x="16" y="52" width="50" height="28" fill="#4A90D9"/><path d="M28 66C32 60 38 60 42 66C46 72 52 72 56 66" fill="none" stroke="#fff" stroke-width="3.4" stroke-linecap="round"/>
    <path d="M24 36C20 42 20 50 22 54" stroke="#fff" stroke-width="3" stroke-linecap="round" opacity=".7"/>`,
  cat_bakery: `
    <path d="M10 56C10 36 32 26 50 26C68 26 90 36 90 56V78C90 83 86 86 82 86H18C14 86 10 83 10 78Z" fill="#D9963F"/>
    <path d="M10 56C10 36 32 26 50 26C68 26 90 36 90 56C74 46 26 46 10 56Z" fill="#EDB765"/>
    <path d="M32 40L40 54M50 36V52M68 40L60 54" stroke="#B87722" stroke-width="4.4" stroke-linecap="round"/>
    <path d="M12 74C14 80 18 82 24 82H80C84 82 88 80 90 74" fill="none" stroke="#B87722" stroke-width="2.4" opacity=".35"/>
    <ellipse cx="26" cy="46" rx="6" ry="3" fill="#fff" opacity=".28" transform="rotate(-30 26 46)"/>`,
  cat_grains: `
    <path d="M24 66H76L82 92H18Z" fill="#E0B070"/><path d="M24 66H76L74 72H26Z" fill="#C98F4E"/>
    <path d="M40 66C40 58 60 58 60 66" fill="#B8762F"/>
    ${wheatEar(-12, -14)}${wheatEar(12, 10)}${wheatEar(0, -2)}
    <path d="M30 80H70" stroke="#B8762F" stroke-width="2.4" stroke-linecap="round" opacity=".5"/>`,
  cat_snacks: `
    <path d="M10 22L40 16L52 76L22 82Z" fill="#E8472F" transform="rotate(-6 30 50)"/>
    <path d="M10 22L40 16L42 28L12 34Z" fill="#B8301D" transform="rotate(-6 30 50)"/>
    <ellipse cx="30" cy="54" rx="11" ry="9" fill="#F4B93A" transform="rotate(-6 30 54)"/>
    <circle cx="62" cy="62" r="25" fill="#D9A25B"/><circle cx="62" cy="62" r="25" fill="none" stroke="#B8762F" stroke-width="2.4" opacity=".5"/>
    <circle cx="54" cy="52" r="3.6" fill="#6B4423"/><circle cx="70" cy="56" r="3.2" fill="#6B4423"/><circle cx="60" cy="68" r="3.6" fill="#6B4423"/>
    <circle cx="74" cy="72" r="3" fill="#6B4423"/><circle cx="48" cy="66" r="2.6" fill="#6B4423"/>
    <ellipse cx="52" cy="46" rx="8" ry="4" fill="#fff" opacity=".25" transform="rotate(-35 52 46)"/>`,
  cat_cooked: `
    <path d="M36 28C30 22 40 16 34 8M52 30C46 22 56 16 50 6M68 28C62 22 72 16 66 8" fill="none" stroke="#9FB0A6" stroke-width="3.4" stroke-linecap="round" opacity=".7"/>
    <ellipse cx="50" cy="52" rx="38" ry="12" fill="#F4B93A"/>
    <circle cx="36" cy="49" r="4.4" fill="#2F9E4F"/><circle cx="52" cy="46" r="4" fill="#E8472F"/><circle cx="66" cy="50" r="4.4" fill="#2F9E4F"/><circle cx="46" cy="55" r="3.4" fill="#fff" opacity=".7"/>
    <path d="M12 52C12 76 28 90 50 90C72 90 88 76 88 52C80 62 20 62 12 52Z" fill="#5B2A6B"/>
    <path d="M16 62C22 70 34 74 50 74" fill="none" stroke="#fff" stroke-width="3" stroke-linecap="round" opacity=".25"/>
    <rect x="38" y="88" width="24" height="5" rx="2.5" fill="#43204F"/>`,
  cat_kitchen_waste: `
    <path d="M22 40H78L72 90C72 93 70 94 67 94H33C30 94 28 93 28 90Z" fill="#5B6B62"/>
    <rect x="18" y="30" width="64" height="12" rx="5" fill="#74857B"/><rect x="42" y="22" width="16" height="8" rx="3" fill="#5B6B62"/>
    <path d="M36 52V82M50 52V82M64 52V82" stroke="#fff" stroke-width="3" stroke-linecap="round" opacity=".25"/>
    <path d="M58 24C60 12 72 6 82 10C80 20 70 26 58 24Z" fill="#2F9E4F"/><path d="M30 26C26 18 32 10 40 8C42 16 38 22 30 26Z" fill="#E8472F"/>`,
  cat_packaging: `
    <path d="M12 34L50 22L88 34V76L50 90L12 76Z" fill="#C98F4E"/>
    <path d="M12 34L50 46L88 34L50 22Z" fill="#DDA867"/><path d="M50 46V90L12 76V34Z" fill="#B8793A"/>
    <path d="M38 27L66 38V50L58 46V40L30 30Z" fill="#F0DDB4"/>
    <path d="M60 64C60 58 68 56 72 60M76 66C78 72 72 78 66 76M68 82C62 84 56 80 56 74" fill="none" stroke="#2F9E4F" stroke-width="3.4" stroke-linecap="round" opacity="0"/>
    <g fill="none" stroke="#fff" stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round" opacity=".85" transform="translate(58 58) scale(.55)">
      <path d="M10 6L22 2L26 14"/><path d="M26 24L16 30L6 24"/><path d="M2 14L2 4"/></g>`,
});

function veg(name, size = 64, extra = "") {
  return `<svg viewBox="0 0 100 100" width="${size}" height="${size}" aria-hidden="true" ${extra}>${VEG[name]}</svg>`;
}

/* Splash: a market crate seen from the front with produce piling in. */
function splashCrate() {
  const slat = (y) => `<rect x="0" y="${y}" width="360" height="30" rx="4" fill="#C98F4E"/>
    <rect x="0" y="${y + 24}" width="360" height="6" fill="#A8723A"/>`;
  return `<svg viewBox="0 0 360 200" preserveAspectRatio="xMidYMax slice" aria-hidden="true">
    ${slat(70)}${slat(104)}${slat(138)}
    <rect x="8" y="62" width="14" height="138" rx="3" fill="#A8723A"/>
    <rect x="338" y="62" width="14" height="138" rx="3" fill="#A8723A"/>
    <circle cx="15" cy="100" r="2.5" fill="#6B4423"/><circle cx="15" cy="140" r="2.5" fill="#6B4423"/>
    <circle cx="345" cy="100" r="2.5" fill="#6B4423"/><circle cx="345" cy="140" r="2.5" fill="#6B4423"/>
  </svg>`;
}

const SPLASH_VEG = [
  ["tomato", 74, 24, 8, -8], ["carrot", 78, 98, 0, 14], ["broccoli", 80, 168, 4, -4],
  ["capsicum", 70, 246, 10, 6], ["eggplant", 78, 292, 0, -10], ["chilli", 54, 4, 44, 20],
  ["greens", 66, 214, 46, 0], ["onion", 56, 142, 40, -6], ["corn", 60, 58, 40, 10],
];
