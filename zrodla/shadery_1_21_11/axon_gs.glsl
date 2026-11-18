// Menu akcesoriów AxonGuns (okno AxonItems w stylu /ustawienia, broń z boku).
// Wspólne dla rendertype_item_entity_translucent_cull (broń i ikony akcesoriów jako ItemDisplay)
// i rendertype_text (kafelki, linie, lista i paski). Wymaga GameTime (uniform albo globals.glsl).
// Stałe muszą zgadzać się z pl.axonitems.gunsmith.GunsmithLayout.
//
// ItemDisplay stoi w oku gracza (jak napisy okna) i ma jasność 13 / 2 (broń) albo 13 / 3 (ikona).
// Przekształcenie encji przesuwa i skaluje model tak, że 1 piksel płótna 640 × 384 = AXON_GS_UNIT bloku:
// płótno x = 320 + x / UNIT, y = 192 - y / UNIT (oś z świata = w stronę gracza w menu).
#define AXON_GS_UNIT 0.25
#define AXON_GS_GUN_LIGHT ivec2(208, 32)
#define AXON_GS_ICON_LIGHT ivec2(208, 48)
// środek obrotu broni przy bujaniu (GunsmithLayout.GUN_X, GUN_Y)
#define AXON_GS_PIVOT vec2(412.0, 182.0)

bool axonGsTime() {
    float t = GameTime * 24000.0;
    return t >= 12000.0 && t < 12140.0;  // AXON_HUD_WINDOW 140 (80–140: klienci z modami, bez zamrażania)
}

// Zegar okna: plugin trzyma czas gry w [12000, 12040) zgodnie z fazą serwera (mod 40), więc co 40 ticków
// (2 s) wraca do tej samej fazy. Bujanie ma okres 2 s albo jego ułamki, żeby nie przeskakiwało.
float axonGsPhase() {
    return mod(GameTime * 24000.0 - 12000.0, 40.0) / 40.0 * 6.2831853;
}

// Obrót bujania (lekkie oddychanie w rękach) i przesunięcie w pikselach płótna.
mat3 axonGsSwayRot() {
    float th = axonGsPhase();
    float rz = 0.0055 * sin(th);              // przechył
    float rx = 0.0100 * sin(th + 1.9);        // góra-dół wokół osi lufy
    float ry = 0.0160 * sin(th + 0.7);        // lekki obrót w bok
    float cz = cos(rz), sz = sin(rz), cx = cos(rx), sx = sin(rx), cy = cos(ry), sy = sin(ry);
    mat3 mz = mat3(cz, sz, 0.0, -sz, cz, 0.0, 0.0, 0.0, 1.0);
    mat3 mx = mat3(1.0, 0.0, 0.0, 0.0, cx, sx, 0.0, -sx, cx);
    mat3 my = mat3(cy, 0.0, -sy, 0.0, 1.0, 0.0, sy, 0.0, cy);
    return my * mx * mz;
}

vec2 axonGsSwayShift() {
    float th = axonGsPhase();
    return vec2(0.8 * sin(th + 2.4), 1.4 * sin(2.0 * th + 0.4));
}

// Punkt broni w płótnie (y w dół) z głębokością z (w stronę gracza) → płótno po bujaniu, z po obrocie.
vec3 axonGsSway(vec2 canvas, float z) {
    vec3 q = axonGsSwayRot() * vec3(canvas.x - AXON_GS_PIVOT.x, AXON_GS_PIVOT.y - canvas.y, z);
    vec2 s = axonGsSwayShift();
    return vec3(AXON_GS_PIVOT.x + q.x + s.x, AXON_GS_PIVOT.y - q.y + s.y, q.z);
}

vec4 axonGsClip(vec2 px, float z) {
    return vec4(px.x / 320.0 - 1.0, 1.0 - px.y / 192.0, z, 1.0);
}

// Linia od kafelka miejsca do kropki na broni (ItemDisplay axon:gs_link, jasność 13 / 4).
// Model to jeden kwadrat 16 × 16 na z = 8 (ściana south), kolor z custom_model_data:
//   R = x kropki / 2 (młodsze 8 bitów), G = y kropki / 2, B = założone | wybrane << 1 | najstarszy bit x << 7.
// Przekształcenie encji niesie resztę (położenie = przesunięcie + skala × (±0,5, ±0,5, 0)):
//   skala x = 1 + 9 × postęp rysowania linii (klient płynnie ją interpoluje),
//   skala y = 1 + x kafelka / 8, przesunięcie z = -(10 + y kafelka / 8).
#define AXON_GS_LINK_LIGHT ivec2(208, 64)
#define AXON_GS_LINK_PAD 7.0
