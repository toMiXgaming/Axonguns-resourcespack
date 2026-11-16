#version 150

#moj_import <minecraft:fog.glsl>

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

uniform mat4 ModelViewMat;
uniform mat4 ProjMat;
uniform int FogShape;
uniform float GameTime;
uniform vec2 ScreenSize;

out float vertexDistance;
out vec4 vertexColor;
out vec2 texCoord0;
flat out int axonMap;
flat out int axonTile;
flat out int axonDensity;
flat out vec2 axonCursor;
flat out vec4 axonSpriteA[AXON_SPRITES];
flat out vec4 axonSpriteB[AXON_SPRITES];
flat out vec2 axonSpriteLim[AXON_SPRITES];
flat out float axonClock;
// Panel HUD AxonScoreboard: 0 = nie, inaczej rodzaj elementu + 1 (opis przy axonHudVertex).
flat out int axonHud;
out vec2 axonHudLocal;
flat out vec4 axonHudBox;
flat out vec3 axonHudBg;
flat out vec3 axonHudHead;
flat out vec3 axonHudAcc;
flat out vec4 axonHudAcc2;
flat out vec4 axonHudExtra;
flat out vec4 axonMiniA;
flat out vec4 axonMiniB;
out vec2 axonMiniL;

// AxonMap: ekran mapy na cały ekran. Musi się zgadzać z pluginem (OverlayLayout).
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
        axonSpriteLim[i] = vec2(0.0);
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
        axonSpriteLim[i] = vec2(float(axonNibbles(base + 15, 3)), float(axonNibbles(base + 18, 3)));
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
const float AXON_HUD_SCALES[4] = float[4](0.75, 1.0, 1.25, 1.5);
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
    float z = Position.z;
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
            axonMiniB.xy = vec2(far ? 1.0 : 0.0, 0.0);
            vec4 rect = axonMiniRect(s);
            float ps = max(4.0, floor(rect.z * 0.09));
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

    vertexDistance = fog_distance(Position, FogShape);
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
        axonSpriteLim[s] = vec2(0.0);
    }

    if (axonHudVertex()) {
        return;
    }
    if (axonMiniVertex()) {
        vertexDistance = 0.0;
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
        vertexDistance = 0.0;
    }
}
