#version 330

#moj_import <minecraft:fog.glsl>
#moj_import <minecraft:dynamictransforms.glsl>
#moj_import <minecraft:projection.glsl>
#moj_import <minecraft:globals.glsl>

#define AXON_SPRITES 5
#define AXON_SPRITE_NIBBLES 21
#define AXON_CLOCK_PERIOD 40.0
const vec3 AXON_NIB[16] = vec3[16](
    vec3(13.0, 13.0, 13.0) / 255.0,
    vec3(255.0, 255.0, 255.0) / 255.0,
    vec3(64.0, 64.0, 255.0) / 255.0,
    vec3(255.0, 0.0, 0.0) / 255.0,
    vec3(127.0, 204.0, 25.0) / 255.0,
    vec3(208.0, 109.0, 142.0) / 255.0,
    vec3(92.0, 219.0, 213.0) / 255.0,
    vec3(48.0, 115.0, 112.0) / 255.0,
    vec3(250.0, 238.0, 77.0) / 255.0,
    vec3(132.0, 44.0, 44.0) / 255.0,
    vec3(0.0, 217.0, 58.0) / 255.0,
    vec3(0.0, 124.0, 0.0) / 255.0,
    vec3(125.0, 53.0, 152.0) / 255.0,
    vec3(160.0, 160.0, 255.0) / 255.0,
    vec3(216.0, 127.0, 51.0) / 255.0,
    vec3(33.0, 33.0, 135.0) / 255.0);

in vec3 Position;
in vec4 Color;
in vec2 UV0;
in ivec2 UV2;

uniform sampler2D Sampler0;
uniform sampler2D Sampler2;

out vec4 axonSm;
#define sphericalVertexDistance axonSm.x
#define cylindricalVertexDistance axonSm.y
#define axonMiniL axonSm.zw
out vec4 vertexColor;
out vec2 texCoord0;
// Varyingi spakowane (NVIDIA: 'cannot locate suitable resource to bind variable', za dużo slotów)
flat out ivec4 axonI;
#define axonMap axonI.x
#define axonTile axonI.y
#define axonDensity axonI.z
#define axonHud axonI.w
flat out vec3 axonCC;
#define axonCursor axonCC.xy
#define axonClock axonCC.z
flat out vec4 axonSpriteA[AXON_SPRITES];
flat out vec4 axonSpriteB[AXON_SPRITES];
flat out vec4 axonSpriteLimP[(AXON_SPRITES + 1) / 2];
// Panel HUD AxonScoreboard: 0 = nie, inaczej rodzaj elementu + 1 (opis przy axonHudVertex).
out vec2 axonHudLocal;
flat out vec4 axonHudBox;
flat out vec3 axonHudBg;
flat out vec3 axonHudHead;
flat out vec3 axonHudAcc;
flat out vec4 axonHudAcc2;
flat out vec4 axonHudExtra;
flat out vec4 axonMiniA;
flat out vec4 axonMiniB;

// AxonMap: ekran mapy na cały ekran. Musi się zgadzać z pluginem (OverlayLayout).
void axonSetLim(int i, vec2 v) {
    if ((i & 1) == 0) axonSpriteLimP[i >> 1].xy = v; else axonSpriteLimP[i >> 1].zw = v;
}

#define AXON_COLS 5
#define AXON_ROWS 3
// Kursor: o ile stopni trzeba obrócić głowę, żeby przejechać całą szerokość / wysokość mapy.
// Plugin ustawia graczowi yaw 0 i pitch 0 przy otwarciu mapy (OverlayLayout.CURSOR_*).
#define AXON_YAW_RANGE 180.0
#define AXON_PITCH_RANGE 100.0

// Sprity: ruchome elementy mini gier rysuje shader (60+ fps), a serwer wysyła tylko tabelę parametrów.
// Tabela leży w ostatnim wierszu kafla (piksel y=127, od x=8): każdy piksel to jeden z 16 kolorów
// (półbajt), rozpoznawany jako najbliższy z AXON_NIB. Pierwsze 4 półbajty to nagłówek; bez niego
// (np. zwykła mapa AxonMap) tabela jest ignorowana.

// Znacznik: w pierwszym wierszu mapy piksele 0-7 to na przemian biały (A) i czarny (B),
// w pikselach 8-23 liczba białych pikseli to numer kafelka, a w ostatnim wierszu
// piksele 0-7 to znowu na przemian A i B. Zwykłe mapy prawie nigdy tak nie wyglądają.
// Ostry ekran (gęstość 2, siatka 10x6 = 1280x768 px, OverlayGrid w AxonOverlay) ma w ostatnim
// wierszu odwrócony wzór (B, A, ...), w pikselach 8-23 numer % 16, a w pikselach 24-31 numer / 16.
int axonDensityOut = 1;

int axonTileIndex() {
    if (textureSize(Sampler0, 0) != ivec2(128, 128)) {
        return -1;
    }
    vec3 a = texelFetch(Sampler0, ivec2(0, 0), 0).rgb;
    vec3 b = texelFetch(Sampler0, ivec2(1, 0), 0).rgb;
    if (min(a.r, min(a.g, a.b)) < 0.95 || max(b.r, max(b.g, b.b)) > 0.15) {
        return -1;
    }
    // Gęstość z pierwszego piksela ostatniego wiersza: A = zwykły ekran 5x3, B = ostry 10x6.
    vec3 last = texelFetch(Sampler0, ivec2(0, 127), 0).rgb;
    int density;
    if (last == a) {
        density = 1;
    } else if (last == b) {
        density = 2;
    } else {
        return -1;
    }
    for (int x = 0; x < 8; x++) {
        vec3 expected = (x % 2 == 0) ? a : b;
        vec3 expectedLast = ((x % 2 == 0) == (density == 1)) ? a : b;
        if (texelFetch(Sampler0, ivec2(x, 0), 0).rgb != expected
                || texelFetch(Sampler0, ivec2(x, 127), 0).rgb != expectedLast) {
            return -1;
        }
    }
    int index = 0;
    for (int x = 8; x < 24; x++) {
        vec3 c = texelFetch(Sampler0, ivec2(x, 0), 0).rgb;
        if (c == a) {
            index++;
        } else if (c != b) {
            return -1;
        }
    }
    if (density == 2) {
        int high = 0;
        for (int x = 24; x < 32; x++) {
            vec3 c = texelFetch(Sampler0, ivec2(x, 0), 0).rgb;
            if (c == a) {
                high++;
            } else if (c != b) {
                return -1;
            }
        }
        index += high * 16;
    }
    axonDensityOut = density;
    return index < AXON_COLS * AXON_ROWS * density * density ? index : -1;
}

int axonNibble(int i) {
    vec3 c = texelFetch(Sampler0, ivec2(8 + i, 127), 0).rgb;
    int best = 0;
    float bestDistance = 1e9;
    for (int k = 0; k < 16; k++) {
        vec3 d = c - AXON_NIB[k];
        float dd = dot(d, d);
        if (dd < bestDistance) {
            bestDistance = dd;
            best = k;
        }
    }
    return best;
}

int axonNibbles(int first, int count) {
    int v = 0;
    for (int i = 0; i < count; i++) {
        v = v * 16 + axonNibble(first + i);
    }
    return v;
}

int axonSigned8(int v) {
    return v >= 128 ? v - 256 : v;
}

void axonReadSprites() {
    for (int i = 0; i < AXON_SPRITES; i++) {
        axonSpriteA[i] = vec4(0.0);
        axonSpriteB[i] = vec4(0.0);
        axonSetLim(i, vec2(0.0));
    }
    if (axonNibble(0) != 10 || axonNibble(1) != 5 || axonNibble(2) != 12 || axonNibble(3) != 3) {
        return;
    }
    for (int i = 0; i < AXON_SPRITES; i++) {
        int base = 4 + i * AXON_SPRITE_NIBBLES;
        int kind = axonNibble(base + 9);
        if (kind == 0) {
            continue;
        }
        // Pozycja to x + 1024 * y (po 10 bitów).
        int xy = axonNibbles(base, 5);
        float y = float(xy / 1024);
        float x = float(xy - (xy / 1024) * 1024);
        float vx = float(axonSigned8(axonNibbles(base + 5, 2))) * 0.25;
        float vy = float(axonSigned8(axonNibbles(base + 7, 2))) * 0.25;
        float color = float(axonNibble(base + 10));
        float size = float(axonNibbles(base + 11, 2));
        float stamp = float(axonNibbles(base + 13, 2));
        axonSpriteA[i] = vec4(x, y, vx, vy);
        axonSpriteB[i] = vec4(float(kind), color, size, stamp);
        axonSetLim(i, vec2(float(axonNibbles(base + 15, 3)), float(axonNibbles(base + 18, 3))));
    }
}

// AxonMap: przy otwartej mapie plugin ustawia graczowi czas gry, którego reszta z 24000 jest
// w [AXON_HUD_TIME, AXON_HUD_TIME + AXON_HUD_WINDOW) (OverlayLayout.HUD_TIME). Wtedy GUI chowa
// hotbar, serduszka, pasek doświadczenia i celownik.
#define AXON_HUD_TIME 12000.0
#define AXON_HUD_WINDOW 60.0

bool axonMapOpen(float gameTime) {
    float t = gameTime * 24000.0;
    return t >= AXON_HUD_TIME && t < AXON_HUD_TIME + AXON_HUD_WINDOW;
}

// Pozycja w pikselach GUI (0,0 w lewym górnym rogu) i rozmiar GUI, z rzutu ortogonalnego.
vec2 axonGuiSize(mat4 proj) {
    return vec2(2.0 / proj[0][0], -2.0 / proj[1][1]);
}

vec2 axonGuiPos(vec4 clip, mat4 proj) {
    return vec2(clip.x + 1.0, 1.0 - clip.y) * 0.5 * axonGuiSize(proj);
}

// Hotbar ze wszystkim nad nim (serduszka, głód, pancerz, doświadczenie) i celownik na środku.
bool axonInHud(vec2 pos, vec2 size, float hudHeight) {
    vec2 center = size * 0.5;
    bool hotbar = abs(pos.x - center.x) <= 92.0 && pos.y >= size.y - hudHeight;
    bool crosshair = abs(pos.x - center.x) <= 8.0 && abs(pos.y - center.y) <= 8.0;
    return hotbar || crosshair;
}

// Poziom doświadczenia nad hotbarem: zielony napis z czarną obwódką.
bool axonIsXpText() {
    vec3 c = floor(Color.rgb * 255.0 + 0.5);
    return c == vec3(128.0, 255.0, 32.0) || c == vec3(0.0);
}

// ---------------------------------------------------------------- panel HUD (AxonScoreboard)
// Plugin wysyła panel jako napis bossbara o szerokości 0: zaczyna się na środku ekranu, y = 3.
// Panel HUD AxonScoreboard (cała tablica to napis jednego bossbara, szerokość 0, start: środek ekranu, y = 3).
// Rodzaj elementu w R / 16 (R 64–191), młodsze 4 bity R to ustawienia (panel: bity 0–1 róg, 2–3 skala;
// baner: bity 0–1 skala). G i B to dane elementu:
//   4 tekst panelu      G = r4 g4, B = b4 suma kontrolna (kolor RGB 4-4-4)
//   5 tło panelu        G = W/2, B = liczba linii | krycie << 4 | alarm << 7
//   6 linia oddzielająca G = W/2, B = numer linii
//   7 pasek             G = wypełnienie 0–255, B = numer linii | kolor << 4 (paleta vanilli, 0 = akcent)
//   8 powiadomienie     G = W/2, B = numer linii | kolor << 5
//   9 tekst banera      jak tekst panelu
//  10 tło banera        G = W/2, B = tick startu & 255
//  11 czas powiadomienia G = tick startu & 255, B = numer linii | długość << 5
// Wszystko poza tekstem to znak kafla skinu (alfa 253 w tle), tekst ma sumę kontrolną, więc zwykłe
// napisy (tytuły okien itd.) nie są ruszane. Musi się zgadzać z AxonScoreboard (pack/HudPanel) i paczką (axoncore/hud.py).
#define AXON_HUD_MARGIN 4.0
#define AXON_MARKER 1024.0   // znaczniki (kafel skinu) mają 1024 × 1024 px GUI, żeby 1.21.6+ rysował tekst nad nimi
#define AXON_LAYER_DY 19.0
const float AXON_HUD_SCALES[4] = float[4](0.5, 0.75, 1.0, 1.25);
const float AXON_BANNER_SCALES[4] = float[4](1.5, 2.0, 2.5, 3.0);
const float AXON_TOAST_TICKS[8] = float[8](40.0, 60.0, 80.0, 100.0, 120.0, 160.0, 200.0, 240.0);

float axonHudSnap(float scale, float gs) {
    // skala do pełnych pikseli ekranu, żeby piksele czcionki były równe
    return max(1.0, floor(scale * gs + 0.5)) / gs;
}

vec2 axonHudPlace(int settings, vec2 local, vec2 guiSize) {
    int corner = settings & 3;
    float gs = ScreenSize.x / guiSize.x;
    float s = axonHudSnap(AXON_HUD_SCALES[(settings >> 2) & 3], gs);
    float top = corner < 2 ? AXON_HUD_MARGIN : floor(guiSize.y * 0.25);
    float x = (corner & 1) == 1 ? guiSize.x - AXON_HUD_MARGIN : AXON_HUD_MARGIN;
    return vec2(x, top) + local * s;
}

vec2 axonBannerPlace(int settings, vec2 local, vec2 guiSize) {
    float gs = ScreenSize.x / guiSize.x;
    float s = axonHudSnap(AXON_BANNER_SCALES[settings & 3], gs);
    return vec2(floor(guiSize.x * 0.5), floor(guiSize.y * 0.36)) + (local - vec2(0.0, 9.0)) * s;
}

int axonHudCheck(int r4, int g4, int b4, int settings) {
    return (r4 + 3 * g4 + 5 * b4 + 7 * settings + 9) & 15;
}

const vec3 AXON_LEGACY[16] = vec3[16](vec3(0.0), vec3(0.0, 0.0, 0.667), vec3(0.0, 0.667, 0.0), vec3(0.0, 0.667, 0.667),
        vec3(0.667, 0.0, 0.0), vec3(0.667, 0.0, 0.667), vec3(1.0, 0.667, 0.0), vec3(0.667),
        vec3(0.333), vec3(0.333, 0.333, 1.0), vec3(0.333, 1.0, 0.333), vec3(0.333, 1.0, 1.0),
        vec3(1.0, 0.333, 0.333), vec3(1.0, 0.333, 1.0), vec3(1.0, 1.0, 0.333), vec3(1.0));
const vec3 AXON_TOAST_COLORS[8] = vec3[8](vec3(0.0), vec3(1.0, 0.3, 0.3), vec3(0.24, 0.86, 0.52), vec3(1.0, 0.78, 0.25),
        vec3(0.22, 0.78, 0.88), vec3(0.69, 0.45, 1.0), vec3(1.0, 0.48, 0.12), vec3(1.0));

bool axonHudSkin(int corner) {
    // kafel skinu 2×2: wierzchołek zna swój róg, więc wylicza lewy górny teksel
    vec2 size = vec2(textureSize(Sampler0, 0));
    vec2 c = vec2(corner == 2 || corner == 3 ? 1.0 : 0.0, corner == 1 || corner == 2 ? 1.0 : 0.0);
    ivec2 tl = ivec2(floor(UV0 * size - c * 2.0 + 0.5));
    axonHudBg = texelFetch(Sampler0, tl, 0).rgb;
    axonHudHead = texelFetch(Sampler0, tl + ivec2(1, 0), 0).rgb;
    axonHudAcc = texelFetch(Sampler0, tl + ivec2(0, 1), 0).rgb;
    axonHudAcc2 = texelFetch(Sampler0, tl + ivec2(1, 1), 0);
    // kafel skinu ma w tle alfę 253: tak się go odróżnia od zwykłych znaków
    return abs(texelFetch(Sampler0, tl, 0).a * 255.0 - 253.0) < 0.5;
}

// Ticki od startu (tick & 255), z zegara gry klienta (serwer synchronizuje go co sekundę).
float axonHudAge(int start) {
    float now = GameTime * 24000.0;
    return mod(now - float(start), 256.0);
}

bool axonHudVertex() {
    if (ProjMat[2][3] != 0.0) {
        return false;
    }
    vec2 guiSize = axonGuiSize(ProjMat);
    vec2 local = Position.xy - vec2(floor(guiSize.x * 0.5), 3.0);
    ivec3 c = ivec3(floor(Color.rgb * 255.0 + 0.5));
    if (c.r < 64 || c.r >= 192) {
        return false;
    }
    int settings = c.r & 15;
    int kind = (c.r - 64) / 16;
    bool banner = kind == 5 || kind == 6;
    bool right = (settings & 1) == 1 && !banner;
    vec2 at = local;
    float z = Position.z + 3.0;   // 1.21.6+: z = 0 leży na dalekiej płaszczyźnie GUI, więc tylko w górę
    if (kind == 0 || kind == 5) {
        // tekst jedzie w drugim bossbarze (tło w pierwszym, żeby 1.21.6+ rysował tekst nad nim), 19 px niżej
        local.y -= AXON_LAYER_DY;
        at = local;
        if (abs(local.x) > 520.0 || local.y < -8.0 || local.y > 330.0) {
            return false;
        }
        // G = r4 g4, B = b4 suma; suma kontrolna chroni zwykłe napisy (np. tytuły okien) o podobnym R
        int r4 = c.g >> 4, g4 = c.g & 15, b4 = c.b >> 4;
        if ((c.b & 15) != axonHudCheck(r4, g4, b4, settings)) {
            return false;
        }
        vertexColor = vec4(vec3(float(r4), float(g4), float(b4)) / 15.0, Color.a);
        axonHud = kind == 0 ? 1 : 9;
        if (banner) {
            z += 50.0;                      // baner nad panelem
        }
    } else {
        int corner = gl_VertexID % 4;   // znaki: lewy górny, lewy dolny, prawy dolny, prawy górny
        vec2 cc = vec2(corner == 2 || corner == 3 ? 1.0 : 0.0, corner == 1 || corner == 2 ? 1.0 : 0.0);
        // znacznik stoi w wierszu bossbara; ten sam napis w czacie (np. odpowiedź komendy) zostaje, gdzie był
        if (abs(local.y - cc.y * AXON_MARKER) > 40.0 || !axonHudSkin(corner)) {
            return false;
        }
        float w = float(c.g * 2);
        float left = right ? -w : 0.0;
        vec2 p;
        if (kind == 1) {
            float h = 21.0 + 9.0 * float(c.b & 15);
            p = vec2(-8.0) + cc * vec2(w + 16.0, h + 16.0);   // 8 px na cień i poświatę alarmu
            at = vec2(left, 0.0) + p;
            axonHudBox = vec4(w, h, float((c.b >> 4) & 7), float(c.b >> 7));
            z -= 2.0;                       // pod tekstem
        } else if (kind == 2) {
            float y = 18.0 + 9.0 * float(c.b & 15) + 3.0;
            p = cc * vec2(w - 12.0, 1.0);
            at = vec2(left + 6.0, y) + p;
            axonHudBox = vec4(w - 12.0, 1.0, 0.0, 0.0);
            z -= 1.0;
        } else if (kind == 3) {
            // pasek: znak stoi tam, gdzie zaczyna się pasek; 30 × 6 px w linii z B
            float x0 = local.x - cc.x * AXON_MARKER;
            float y = 18.0 + 9.0 * float(c.b & 15) + 1.0;
            p = vec2(-2.0) + cc * vec2(34.0, 10.0);
            at = vec2(x0, y) + p;
            int pal = c.b >> 4;
            axonHudExtra = vec4(pal == 0 ? axonHudAcc : AXON_LEGACY[pal], float(c.g) / 255.0);
            axonHudBox = vec4(30.0, 6.0, 0.0, 0.0);
            z -= 1.0;
        } else if (kind == 4) {
            float y = 18.0 + 9.0 * float(c.b & 31) - 4.0;
            p = vec2(-6.0) + cc * vec2(w + 12.0, 28.0);
            at = vec2(local.x - cc.x * AXON_MARKER, y) + p;   // znak stoi na lewej krawędzi (wysuwanie robi serwer)
            int pal = c.b >> 5;
            axonHudExtra = vec4(pal == 0 ? axonHudAcc : AXON_TOAST_COLORS[pal], 0.0);
            axonHudBox = vec4(w, 16.0, 0.0, 0.0);
            z -= 2.0;
        } else if (kind == 6) {
            float age = axonHudAge(c.b);
            p = vec2(-w * 0.5 - 40.0, -14.0) + cc * vec2(w + 80.0, 46.0);
            at = p;
            axonHudBox = vec4(w, 18.0, age, 0.0);
            z -= 3.0;                       // pod tłem panelu: panel i jego tekst przykrywają pas banera
        } else if (kind == 7) {
            float y = 18.0 + 9.0 * float(c.b & 31) - 4.0;
            float age = axonHudAge(c.g);
            float total = AXON_TOAST_TICKS[c.b >> 5];
            p = cc * vec2(3.0, 16.0);
            at = vec2(local.x - cc.x * AXON_MARKER, y) + p;   // pionowy pasek czasu przy lewej krawędzi powiadomienia
            axonHudExtra = vec4(axonHudAcc, clamp(1.0 - age / total, 0.0, 1.0));
            axonHudBox = vec4(3.0, 16.0, age, 0.0);
            z -= 1.0;
        } else {
            return false;
        }
        axonHudLocal = p;
        axonHud = kind + 1;
    }
    vec2 pos = banner ? axonBannerPlace(settings, at, guiSize) : axonHudPlace(settings, at, guiSize);
    gl_Position = ProjMat * ModelViewMat * vec4(pos, z, 1.0);
    return true;
}

const float AXON_MINI_RANGE[4] = float[4](32.0, 64.0, 96.0, 128.0);
// ── Minimapa AxonMap ─────────────────────────────────────────────────────────────────────────────
// Znaki czcionki axonmap:minimapa stoją w niewidzialnym wyświetlaczu tekstu przy graczu (kotwica w punkcie siatki
// co 16 bloków). W świecie wierzchołek ma Position = położenie względem kamery, więc shader zna pozycję i kierunek
// kamery w każdej klatce: mapa przesuwa się i obraca płynnie, bez czekania na serwer.
//   kafel terenu 128 × 128 (alfa 250 w lewym górnym tekselu), kolor: F | ustawienia 8 | dx 3 | dz 3 | ax 3 | az 3
//   znacznik / ramka: teksel 1 × 1 z alfą 249, R = ustawienia, G = rola (1 tło, 2 wierzch, 3 znacznik);
//   znacznik ma kolor E | rodzaj 3 | daleko 1, G = dx + 128, B = dz + 128 (bloki od kotwicy, przy zasięgu 96+ co 2 bloki)
//   ustawienia: róg 2 | rozmiar 2 | zasięg 2 | koło 1 | obrót 1
const float AXON_MINI_SIDE[4] = float[4](0.20, 0.27, 0.35, 0.45);
const float AXON_MINI_PAD = 0.07;

vec4 axonMiniRect(int s) {
    float unit = ScreenSize.y;
    float hs = floor(AXON_MINI_SIDE[(s >> 2) & 3] * unit * 0.5);
    float m = floor(0.025 * unit);
    int corner = s & 3;
    float cx = (corner & 1) == 1 ? ScreenSize.x - m - hs : m + hs;
    float cy = corner >= 2 ? ScreenSize.y - m - hs - floor(0.14 * unit) : m + hs;
    return vec4(cx, cy, hs, 0.0);
}

vec4 axonMiniClip(vec2 px, float z) {
    return vec4(px.x / ScreenSize.x * 2.0 - 1.0, 1.0 - px.y / ScreenSize.y * 2.0, z, 1.0);
}

vec2 axonMiniFacing() {
    // przód kamery w poziomie; patrząc pionowo w dół/górę bierzemy wektor „do góry” kamery
    vec3 fwd = -vec3(ModelViewMat[0][2], ModelViewMat[1][2], ModelViewMat[2][2]);
    vec3 up = vec3(ModelViewMat[0][1], ModelViewMat[1][1], ModelViewMat[2][1]);
    vec2 f = fwd.xz - up.xz * fwd.y;
    return length(f) > 1e-4 ? normalize(f) : vec2(0.0, 1.0);
}

// ── Kompas AxonMap ───────────────────────────────────────────────────────────────────────────────
// Pasek kompasu u góry ekranu. Znaki to te same znaczniki 1 × 1 (alfa 249) co ramka minimapy, ale kolor ma R od 0xF0:
//   teksel: R = ustawienia kompasu: rozmiar 2 | zakres 1 (0 = 180°, 1 = 120°) | wolny 1 | wykładnik 4
//   wykładnik 15 to pasek; inaczej cel: R = F | bez napisu 1 | rodzaj znacznika minimapy 3,
//   G = dx + 128, B = dz + 128, przesunięcie od kotwicy = (dx, dz) × 2^wykładnik bloków
// Kierunek kamery i położenie celu względem kamery shader liczy w każdej klatce, więc pasek obraca się płynnie.
const float AXON_COMPASS_W[3] = float[3](0.34, 0.44, 0.56);
const float AXON_COMPASS_H[3] = float[3](0.026, 0.032, 0.040);

// Kierunek jak w grach: 0 = północ (-Z), 90 = wschód (+X).
float axonHeading(vec2 d) {
    return degrees(atan(d.x, -d.y));
}

bool axonCompassVertex(ivec3 c, vec2 cv, vec2 atlas, vec2 f) {
    ivec2 t1 = ivec2(floor(UV0 * atlas - cv + 0.5));
    vec4 tx = texelFetch(Sampler0, t1, 0);
    if (abs(tx.a * 255.0 - 249.0) > 0.5) {
        return false;
    }
    int s = int(tx.r * 255.0 + 0.5);
    int e = (s >> 4) & 15;
    int size = min(s & 3, 2);
    float span = ((s >> 2) & 1) == 1 ? 120.0 : 180.0;
    float unit = ScreenSize.y;
    float halfW = min(floor(AXON_COMPASS_W[size] * unit * 0.5), floor(ScreenSize.x * 0.46));
    float bh = floor(AXON_COMPASS_H[size] * unit);
    float gp = max(1.0, floor(bh * 0.45 / 7.0 + 0.5));
    vec2 top = vec2(floor(ScreenSize.x * 0.5), floor(0.012 * unit) + 1.0);
    float heading = axonHeading(f);
    vec2 l;
    if (e == 15) {
        // pasek: od lewej do prawej krawędzi, pod nim okienko z kierunkiem w stopniach
        vec2 lo = vec2(-halfW - 2.0, -2.0);
        vec2 hi = vec2(halfW + 2.0, bh + 13.0 * gp + 2.0);
        l = mix(lo, hi, cv);
        axonMiniA = vec4(heading, span, 6.0, float(s));
        axonMiniB = vec4(halfW, bh, gp, 0.0);
        gl_Position = axonMiniClip(top + l, -0.986);
    } else {
        vec2 rel = vec2(float(c.g - 128), float(c.b - 128)) * exp2(float(e)) + Position.xz;
        float dist = length(rel);
        float d = mod(axonHeading(rel) - heading + 540.0, 360.0) - 180.0;
        float x = d / (span * 0.5) * halfW;
        float ih = floor(bh * 0.36);
        float lim = halfW - ih - 3.0;
        float side = 0.0;
        if (abs(x) > lim) {
            side = sign(x);
            x = side * lim;
        }
        // pod paskiem odległość (do 4 znaków po 6 pikseli czcionki); przy środku zjeżdża pod okienko stopni
        float label = float((c.r >> 3) & 1);
        if (label < 0.5 && abs(x) < 29.0 * gp) {
            label = 2.0;
        }
        float qx = max(ih, 14.0 * gp) + 2.0;
        vec2 lo = vec2(-qx, -ih - 2.0);
        vec2 hi = vec2(qx, bh * 0.5 + 25.0 * gp + 2.0);
        l = mix(lo, hi, cv);
        axonMiniA = vec4(dist, side, 7.0 + float(c.r & 7) / 16.0, float(s));
        axonMiniB = vec4(ih, gp, bh * 0.5, label);
        // bliższy cel leży wyżej, więc przy nachodzących znacznikach widać jego odległość
        float z = -0.9880 - 0.0009 * (1.0 - dist / (dist + 200.0));
        gl_Position = dist < 2.5 ? vec4(-10.0, -10.0, -10.0, 1.0)
                : axonMiniClip(top + vec2(x, bh * 0.5) + l, z);
    }
    axonMiniL = l;
    vertexColor = vec4(1.0);
    texCoord0 = UV0;
    return true;
}

bool axonMiniVertex() {
    if (ProjMat[2][3] == 0.0) {
        return false;
    }
    ivec3 c = ivec3(floor(Color.rgb * 255.0 + 0.5));
    int kind = c.r >> 4;
    if (kind < 14) {
        return false;
    }
    int vc = gl_VertexID % 4;
    vec2 cv = vec2(vc == 2 || vc == 3 ? 1.0 : 0.0, vc == 1 || vc == 2 ? 1.0 : 0.0);
    vec2 atlas = vec2(textureSize(Sampler0, 0));
    vec2 f = axonMiniFacing();
    int s;
    float z;
    vec2 l;
    if (kind == 15) {
        // znak kompasu (teksel 1 × 1 z alfą 249) albo kafel terenu (128 × 128, alfa 250 w lewym górnym tekselu)
        if (axonCompassVertex(c, cv, atlas, f)) {
            return true;
        }
        ivec2 t0 = ivec2(floor(UV0 * atlas - cv * 128.0 + 0.5));
        if (abs(texelFetch(Sampler0, t0, 0).a * 255.0 - 250.0) > 0.5) {
            return false;
        }
        int bits = (c.r & 15) << 16 | c.g << 8 | c.b;
        s = (bits >> 12) & 255;
        vec2 d = vec2(float(((bits >> 9) & 7) - 2), float(((bits >> 6) & 7) - 2));
        vec2 a = vec2(float((bits >> 3) & 7), float(bits & 7)) * 16.0;
        axonMiniA = vec4(a - Position.xz - d * 128.0, 5.0, float(s));
        axonMiniB = vec4(vec2(t0), f);
        l = cv * 2.0 - 1.0;
        z = -0.992;
    } else {
        ivec2 t0 = ivec2(floor(UV0 * atlas - cv + 0.5));
        vec4 tx = texelFetch(Sampler0, t0, 0);
        if (abs(tx.a * 255.0 - 249.0) > 0.5) {
            return false;
        }
        s = int(tx.r * 255.0 + 0.5);
        int role = int(tx.g * 255.0 + 0.5);
        axonMiniB = vec4(0.0, 0.0, f);
        if (role == 3) {
            // znacznik: pozycja względem kamery = przesunięcie od kotwicy + Position
            float range = AXON_MINI_RANGE[(s >> 4) & 3];
            // przy zasięgu 96 i 128 bloków jednostka przesunięcia to 2 bloki (mieści ±254)
            float unit = ((s >> 4) & 3) >= 2 ? 2.0 : 1.0;
            vec2 rel = vec2(float(c.g - 128), float(c.b - 128)) * unit + Position.xz;
            vec2 r = vec2(-f.y, f.x);
            vec2 p = ((s >> 7) & 1) == 1 ? vec2(dot(rel, r), -dot(rel, f)) : rel;
            p /= range;
            bool far = (c.r & 1) == 1;
            float edge = ((s >> 6) & 1) == 1 ? length(p) : max(abs(p.x), abs(p.y));
            if (far || edge > 0.9) {
                p *= 0.9 / max(edge, 1e-4);
                far = true;
            }
            axonMiniA = vec4(p, 3.0 + float((c.r >> 1) & 7) / 16.0, float(s));
            axonMiniB.xy = vec2(far ? 1.0 : 0.0, atan(p.y, p.x));   // kierunek grota dla znacznika poza mapą
            vec4 rect = axonMiniRect(s);
            float ps = max(5.0, floor(rect.z * 0.1));
            l = cv * 2.0 - 1.0;
            gl_Position = axonMiniClip(rect.xy + p * rect.z + l * ps, -0.995);
            axonMiniL = l;
            vertexColor = vec4(1.0);
            texCoord0 = UV0;
            return true;
        }
        axonMiniA = vec4(0.0, 0.0, float(role), float(s));
        l = (cv * 2.0 - 1.0) * (1.0 + AXON_MINI_PAD);
        z = role == 1 ? -0.990 : -0.997;
    }
    vec4 rect = axonMiniRect(s);
    gl_Position = axonMiniClip(rect.xy + l * rect.z, z);
    axonMiniL = l;
    vertexColor = vec4(1.0);
    texCoord0 = UV0;
    return true;
}

// ── Okno UI AxonItems (/ustawienia) ─────────────────────────────────────────────────────────────
// Napisy i pudełka okna to encje tekstowe (TextDisplay) tylko dla gracza: billboard CENTER w miejscu
// oka gracza, przesunięte o AXON_UI_DEPTH bloków przed kamerę, skala 10 (1 piksel czcionki = AXON_UI_UNIT
// bloku = 1 piksel płótna 640 × 384). Shader przenosi je na ekran nad kafle mapy, więc tekst jest ostry,
// a podświetlenie pod kursorem i kursor liczy klient w każdej klatce (serwer zmienia tylko stan po kliknięciu).
// Rozpoznanie: perspektywa, otwarte pełne GUI (axonMapOpen), alfa koloru 252/253 (text opacity encji)
// i odległość w widoku ~AXON_UI_DEPTH.
//   alfa 253: napis; kolor #010203 to niewidoczny wypełniacz (ustala lewą krawędź wyrównania)
//   alfa 252: pudełko; jeden znak = jedno pudełko: R = x / 2 (młodsze 8 bitów), G = y / 2,
//             B = styl 5 bitów | stan 2 bity << 5 | najstarszy bit x / 2 << 7
//             stan: 0 zwykły, 1 aktywny, 2 wyłączony, 3 wciśnięty/zaznaczony
#define AXON_UI_DEPTH 16.0
#define AXON_UI_UNIT 0.25
#define AXON_UI_STYLES 32
// szerokość, wysokość, promień rogu, głębia (bliżej = bardziej ujemna)
const vec4 AXON_UI_STYLE[AXON_UI_STYLES] = vec4[AXON_UI_STYLES](
    vec4(640.0, 384.0, 0.0, -0.9900),    // 0 przyciemniona szyba (cały ekran, rysowana pierwsza)
    vec4(176.0, 384.0, 0.0, -0.9905),    // 1 szyna z kartami (lewa krawędź ekranu)
    vec4(172.0, 292.0, 10.0, -0.9910),   // 2 karta szczegółów
    vec4(160.0, 26.0, 6.0, -0.9920),     // 3 karta pluginu w szynie
    vec4(104.0, 22.0, 6.0, -0.9920),     // 4 zakładka (podkreślenie)
    vec4(244.0, 26.0, 5.0, -0.9920),     // 5 wiersz ustawienia
    vec4(30.0, 13.0, 3.0, -0.9925),      // 6 klawisz
    vec4(26.0, 22.0, 7.0, -0.9920),      // 7 zamknij
    vec4(20.0, 20.0, 0.0, -0.9990),      // 8 kursor
    vec4(146.0, 1.0, 0.5, -0.9915),      // 9 linia
    vec4(140.0, 16.0, 8.0, -0.9920),     // 10 plakietka
    vec4(30.0, 16.0, 8.0, -0.9930),      // 11 przełącznik (stan 1 = włączony)
    vec4(22.0, 22.0, 0.0, -0.9930),      // 12 ikona: mapa (kompas)
    vec4(22.0, 22.0, 0.0, -0.9930),      // 13 ikona: tablica (lista)
    vec4(22.0, 22.0, 0.0, -0.9930),      // 14 ikona: bronie (celownik)
    vec4(22.0, 22.0, 0.0, -0.9930),      // 15 ikona: rozmowy (dymek)
    vec4(22.0, 22.0, 0.0, -0.9930),      // 16 ikona: wygląd (paleta)
    vec4(22.0, 22.0, 0.0, -0.9930),      // 17 ikona: zębatka
    vec4(22.0, 22.0, 0.0, -0.9930),      // 18 ikona: gwiazdka
    vec4(22.0, 22.0, 0.0, -0.9930),      // 19 ikona: strzałka dalej
    vec4(22.0, 22.0, 0.0, -0.9930),      // 20 ikona: lupa
    vec4(22.0, 22.0, 0.0, -0.9930),      // 21 ikona: serce
    vec4(22.0, 22.0, 0.0, -0.9930),      // 22 ikona: dom
    vec4(22.0, 22.0, 0.0, -0.9930),      // 23 ikona: rdzeń
    vec4(22.0, 22.0, 0.0, -0.9930),      // 24 ikona: krzyż
    vec4(22.0, 22.0, 0.0, -0.9930),      // 25 ikona: ramka
    vec4(22.0, 22.0, 0.0, -0.9930),      // 26 ikona: zegar
    vec4(22.0, 22.0, 0.0, -0.9930),      // 27 ikona: start
    vec4(22.0, 22.0, 0.0, -0.9930),      // 28 ikona: tarcza
    vec4(22.0, 22.0, 0.0, -0.9930),      // 29 ikona: oko
    vec4(22.0, 22.0, 0.0, -0.9930),      // 30 ikona: informacja
    vec4(22.0, 22.0, 0.0, -0.9930));      // 31 ikona: flaga

vec4 axonUiClip(vec2 px, float z) {
    return vec4(px.x / 320.0 - 1.0, 1.0 - px.y / 192.0, z, 1.0);
}

bool axonUiVertex() {
    if (ProjMat[2][3] == 0.0 || !axonMapOpen(GameTime)) {
        return false;
    }
    float a = floor(Color.a * 255.0 + 0.5);
    if (a < 251.5 || a > 253.5) {
        return false;
    }
    vec4 view = ModelViewMat * vec4(Position, 1.0);
    if (abs(abs(view.z) - AXON_UI_DEPTH) > 3.0) {
        return false;
    }
    ivec3 c = ivec3(floor(Color.rgb * 255.0 + 0.5));
    if (a > 252.5) {
        if (c == ivec3(1, 2, 3)) {
            gl_Position = vec4(-10.0, -10.0, -10.0, 1.0);
            return true;
        }
        vec2 px = vec2(320.0 + view.x / AXON_UI_UNIT, 192.0 - view.y / AXON_UI_UNIT);
        gl_Position = axonUiClip(px, -0.9960);
        vertexColor = vec4(Color.rgb, 1.0);
        texCoord0 = UV0;
        return true;
    }
    int style = min(c.b & 31, AXON_UI_STYLES - 1);
    int state = (c.b >> 5) & 3;
    vec2 org = vec2(float(c.r | ((c.b >> 7) << 8)), float(c.g)) * 2.0;
    vec4 st = AXON_UI_STYLE[style];
    // kursor jak w kaflach mapy: z obrotu kamery, w pikselach płótna 640 × 384
    vec3 forward = -vec3(ModelViewMat[0][2], ModelViewMat[1][2], ModelViewMat[2][2]);
    float yaw = degrees(atan(-forward.x, forward.z));
    float pitch = degrees(asin(clamp(-forward.y, -1.0, 1.0)));
    axonCursor = clamp(vec2(0.5 + yaw / AXON_YAW_RANGE, 0.5 + pitch / AXON_PITCH_RANGE), 0.0, 1.0);
    vec2 cur = axonCursor * vec2(640.0, 384.0);
    int vc = gl_VertexID % 4;
    vec2 cv = vec2(vc == 2 || vc == 3 ? 1.0 : 0.0, vc == 1 || vc == 2 ? 1.0 : 0.0);
    float pad = style == 0 ? 0.0 : (style == 11 ? 2.0 : (style >= 12 ? 7.0 : 10.0));
    if (style == 8) {
        org = cur - vec2(3.0);
        pad = 0.0;
        axonHud = 21;
    } else {
        axonHud = 20;
    }
    vec2 local = mix(vec2(-pad), st.xy + pad, cv);
    gl_Position = axonUiClip(org + local, st.w);
    axonHudLocal = local;
    axonHudBox = vec4(st.xy, float(style), float(state));
    axonHudExtra = vec4(org, st.z, 0.0);
    vertexColor = vec4(1.0);
    texCoord0 = UV0;
    return true;
}

void main() {
    gl_Position = ProjMat * ModelViewMat * vec4(Position, 1.0);
    axonHud = 0;
    axonHudLocal = vec2(0.0);
    axonHudBox = vec4(0.0);
    axonHudBg = vec3(0.0);
    axonHudHead = vec3(0.0);
    axonHudAcc = vec3(0.0);
    axonHudAcc2 = vec4(0.0);
    axonHudExtra = vec4(0.0);
    axonMiniA = vec4(0.0);
    axonMiniB = vec4(0.0);
    axonMiniL = vec2(0.0);

    sphericalVertexDistance = fog_spherical_distance(Position);
    cylindricalVertexDistance = fog_cylindrical_distance(Position);
    vertexColor = Color * texelFetch(Sampler2, UV2 / 16, 0);
    texCoord0 = UV0;
    axonMap = 0;
    axonTile = 0;
    axonDensity = 1;
    axonCursor = vec2(-1.0);
    axonClock = mod(GameTime * 24000.0 - 12000.0, AXON_CLOCK_PERIOD);
    for (int s = 0; s < AXON_SPRITES; s++) {
        axonSpriteA[s] = vec4(0.0);
        axonSpriteB[s] = vec4(0.0);
        axonSetLim(s, vec2(0.0));
    }

    if (axonHudVertex()) {
        if (axonHud != 0 && axonMapOpen(GameTime)) {
            gl_Position = vec4(-10.0, -10.0, -10.0, 1.0);   // panel tablicy chowa się przy pełnej mapie AxonMap
        }
        return;
    }
    if (axonUiVertex()) {
        sphericalVertexDistance = 0.0;
        cylindricalVertexDistance = 0.0;
        return;
    }
    if (axonMiniVertex()) {
        if (axonMapOpen(GameTime)) {
            // minimapa i kompas chowają się przy pełnym ekranie (mapa AxonMap, warsztaty, skrzynie i inne GUI AxonOverlay)
            gl_Position = vec4(-10.0, -10.0, -10.0, 1.0);
        }
        sphericalVertexDistance = 0.0;
        cylindricalVertexDistance = 0.0;
        return;
    }

    if (ProjMat[2][3] == 0.0 && axonMapOpen(GameTime) && axonIsXpText()
            && axonInHud(axonGuiPos(gl_Position, ProjMat), axonGuiSize(ProjMat), 40.0)) {
        gl_Position = vec4(-10.0, -10.0, -10.0, 1.0);
        return;
    }

    int tile = axonTileIndex();
    if (tile >= 0) {
        axonMap = 1;
        axonTile = tile;
        axonDensity = axonDensityOut;
        axonReadSprites();
        // Kierunek kamery z ModelViewMat (świat -> widok): przód = -trzeci wiersz macierzy.
        vec3 forward = -vec3(ModelViewMat[0][2], ModelViewMat[1][2], ModelViewMat[2][2]);
        float yaw = degrees(atan(-forward.x, forward.z));
        float pitch = degrees(asin(clamp(-forward.y, -1.0, 1.0)));
        axonCursor = clamp(vec2(0.5 + yaw / AXON_YAW_RANGE, 0.5 + pitch / AXON_PITCH_RANGE), 0.0, 1.0);
        // Mapa wypełnia cały ekran (przy 16:9 jest lekko rozciągnięta w poziomie).
        int cols = AXON_COLS * axonDensity;
        int rows = AXON_ROWS * axonDensity;
        vec2 tileSize = vec2(2.0 / float(cols), 2.0 / float(rows));
        int tx = tile % cols;
        int ty = tile / cols;
        vec2 topLeft = vec2(-1.0 + float(tx) * tileSize.x, 1.0 - float(ty) * tileSize.y);
        gl_Position = vec4(topLeft + vec2(UV0.x * tileSize.x, -UV0.y * tileSize.y), -0.99, 1.0);
        sphericalVertexDistance = 0.0;
        cylindricalVertexDistance = 0.0;
    }
}
