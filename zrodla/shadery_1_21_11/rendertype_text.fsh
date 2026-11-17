#version 330

#moj_import <minecraft:fog.glsl>
#moj_import <minecraft:dynamictransforms.glsl>
#moj_import <minecraft:globals.glsl>

// Musi się zgadzać z rendertype_text.vsh.
#define AXON_COLS 5
#define AXON_ROWS 3
#define AXON_SPRITES 5
#define AXON_CLOCK_PERIOD 40.0

uniform sampler2D Sampler0;

in vec4 axonSm;
#define sphericalVertexDistance axonSm.x
#define cylindricalVertexDistance axonSm.y
#define axonMiniL axonSm.zw
in vec4 vertexColor;
in vec2 texCoord0;
// Varyingi spakowane (NVIDIA: 'cannot locate suitable resource to bind variable', za dużo slotów)
flat in ivec4 axonI;
#define axonMap axonI.x
#define axonTile axonI.y
#define axonDensity axonI.z
#define axonHud axonI.w
flat in vec3 axonCC;
#define axonCursor axonCC.xy
#define axonClock axonCC.z
flat in vec4 axonSpriteA[AXON_SPRITES];
flat in vec4 axonSpriteB[AXON_SPRITES];
flat in vec4 axonSpriteLimP[(AXON_SPRITES + 1) / 2];
in vec2 axonHudLocal;
flat in vec4 axonHudBox;
flat in vec3 axonHudBg;
flat in vec3 axonHudHead;
flat in vec3 axonHudAcc;
flat in vec4 axonHudAcc2;
flat in vec4 axonHudExtra;
flat in vec4 axonMiniA;
flat in vec4 axonMiniB;

out vec4 fragColor;


// ---------------------------------------------------------------- sprity
// Ruchome elementy mini gier. Serwer zapisuje parametry w ostatnim wierszu kafla (rendertype_text.vsh),
// a tutaj rysujemy je w każdej klatce klienta. Pozycja = (x, y) w chwili "stamp" + prędkość * czas, który
// minął na zegarze klienta. Rodzaje:
//  1 znacznik skali       2 rozżarzony pręt     3 płomienie       4 pulsujący cel
//  5 narzędzie przy kursorze (rozmiar = numer narzędzia, lo = 1 gdy narzędzie pracuje, x/y = punkt zaczepienia)
//  6 siatka celownika optyki (lo = procent przytrzymania)       7 ruchomy cel optyki (rozmiar = tolerancja)
// Animacje mają okres będący dzielnikiem 40 ticków, więc zawinięcie zegara jest niewidoczne.

const float AXON_TAU = 6.2831853;

vec3 axonEffectColor(int index, float heat) {
    if (index == 15) {
        vec3 cold = vec3(96.0, 104.0, 116.0) / 255.0;
        vec3 red = vec3(200.0, 60.0, 30.0) / 255.0;
        vec3 hot = vec3(255.0, 240.0, 190.0) / 255.0;
        return heat < 0.5 ? mix(cold, red, heat * 2.0) : mix(red, hot, (heat - 0.5) * 2.0);
    }
    if (index == 1) return vec3(52.0, 210.0, 123.0) / 255.0;
    if (index == 2) return vec3(239.0, 74.0, 74.0) / 255.0;
    if (index == 3) return vec3(255.0, 209.0, 102.0) / 255.0;
    if (index == 4) return vec3(94.0, 214.0, 224.0) / 255.0;
    if (index == 5) return vec3(255.0, 138.0, 61.0) / 255.0;
    if (index == 6) return vec3(150.0, 160.0, 172.0) / 255.0;
    if (index == 7) return vec3(150.0, 200.0, 255.0) / 255.0;
    if (index == 8) return vec3(86.0, 150.0, 255.0) / 255.0;
    if (index == 9) return vec3(52.0, 210.0, 123.0) / 255.0;
    if (index == 10) return vec3(255.0, 106.0, 90.0) / 255.0;
    if (index == 11) return vec3(188.0, 120.0, 255.0) / 255.0;
    if (index == 12) return vec3(255.0, 196.0, 70.0) / 255.0;
    if (index == 13) return vec3(70.0, 214.0, 214.0) / 255.0;
    if (index == 14) return vec3(255.0, 200.0, 110.0) / 255.0;
    return vec3(241.0, 244.0, 249.0) / 255.0;
}

void axonBlend(inout vec3 base, vec3 color, float alpha) {
    base = mix(base, color, clamp(alpha, 0.0, 1.0));
}

float axonHash(float n) {
    return fract(sin(n) * 43758.5453);
}

vec2 axonRot(vec2 p, float degreesCcw) {
    float a = radians(degreesCcw);
    float c = cos(a);
    float s = sin(a);
    return vec2(c * p.x + s * p.y, -s * p.x + c * p.y);
}

// Zaokrąglony prostokąt od (x, y) o rozmiarze (w, h) i promieniu r: odległość ze znakiem.
float axonRect(vec2 p, float x, float y, float w, float h, float r) {
    vec2 c = vec2(x + w * 0.5, y + h * 0.5);
    vec2 q = abs(p - c) - vec2(w * 0.5 - r, h * 0.5 - r);
    return length(max(q, 0.0)) + min(max(q.x, q.y), 0.0) - r;
}

float axonSegment(vec2 p, vec2 a, vec2 b) {
    vec2 pa = p - a;
    vec2 ba = b - a;
    float h = clamp(dot(pa, ba) / max(dot(ba, ba), 1e-4), 0.0, 1.0);
    return length(pa - ba * h);
}

float axonCover(float d, float px) {
    return clamp(0.5 - d / px, 0.0, 1.0);
}

// Kształt z pionowym gradientem koloru (od góry y0 do dołu y1).
void axonShape(inout vec3 base, float d, float px, vec2 p, float y0, float y1, vec3 top, vec3 bottom) {
    float k = clamp((p.y - y0) / max(y1 - y0, 1e-3), 0.0, 1.0);
    axonBlend(base, mix(top, bottom, k), axonCover(d, px));
}

void axonGlow(inout vec3 base, vec2 p, vec2 c, float radius, vec3 color, float alpha) {
    axonBlend(base, color, alpha * clamp(1.0 - length(p - c) / radius, 0.0, 1.0));
}

void axonSparks(inout vec3 base, vec2 p, vec2 c, float strength, vec3 color, float px) {
    if (length(p - c) > 40.0) {
        return;
    }
    float seed = floor(axonClock * 0.7);
    for (int i = 0; i < 9; i++) {
        float a = axonHash(seed * 13.17 + float(i) * 7.31) * AXON_TAU;
        float d = 4.0 + axonHash(seed * 5.71 + float(i) * 3.13) * 22.0 * strength;
        vec2 dir = vec2(cos(a), sin(a));
        vec2 from = c + dir * d * 0.4;
        vec2 to = c + dir * d + vec2(0.0, -3.0);
        axonBlend(base, color, 0.9 * axonCover(axonSegment(p, from, to) - 0.7, px));
    }
}

vec3 axonRgb(float r, float g, float b) {
    return vec3(r, g, b) / 255.0;
}

void axonTool(inout vec3 base, vec2 p, float px, vec2 cursor, int tool, bool on, vec3 color, vec2 anchor) {
    vec2 q = p - cursor;
    if (tool == 9) {
        // przeciągana część (układanie): przerywana linia od miejsca części do kursora i część przy kursorze
        float t = dot(p - anchor, normalize(cursor - anchor + 1e-4));
        float dash = step(0.5, fract(t / 10.0 - axonClock / 40.0 * 4.0));
        axonBlend(base, color, 0.6 * dash * axonCover(axonSegment(p, anchor, cursor) - 0.8, px));
        if (length(q) > 40.0) return;
        axonBlend(base, vec3(0.0), 0.27 * axonCover(length(q * vec2(1.0, 1.1) - vec2(0.0, 3.0)) - 23.0, px));
        float d = axonRect(q, -22.0, -22.0, 44.0, 44.0, 8.0);
        axonShape(base, d, px, q, -22.0, 22.0, clamp(color * 1.15, 0.0, 1.0), color * 0.7);
        axonBlend(base, vec3(1.0), 0.9 * axonCover(abs(d + 0.7) - 0.7, px));
        float ang = atan(q.y, q.x) - axonClock * AXON_TAU / 40.0 * 2.0;
        float teeth = 11.0 + 2.0 * step(0.0, sin(ang * 8.0));
        float gear = max(length(q) - teeth, 4.0 - length(q));
        axonBlend(base, vec3(1.0), 0.84 * axonCover(gear, px));
        return;
    }
    if (length(q) > 90.0) return;
    if (tool == 1) {
        // śrubokręt
        vec2 r = axonRot(q - vec2(4.0, on ? 3.0 : 0.0), 35.0);
        axonShape(base, axonRect(r, -3.0, 6.0, 6.0, 16.0, 2.0), px, r, 6.0, 22.0, axonRgb(190.0, 196.0, 206.0), axonRgb(150.0, 156.0, 166.0));
        float h = axonRect(r, -8.0, 22.0, 16.0, 34.0, 7.0);
        axonShape(base, h, px, r, 22.0, 56.0, axonRgb(255.0, 160.0, 80.0), axonRgb(190.0, 80.0, 30.0));
        axonBlend(base, axonRgb(60.0, 30.0, 14.0), axonCover(abs(h + 0.5) - 0.5, px));
    } else if (tool == 2) {
        // młotek: przy uderzeniu przechylony do przodu
        vec2 r = axonRot(q, on ? 20.0 : -40.0);
        axonShape(base, axonRect(r, -3.0, -52.0, 6.0, 52.0, 3.0), px, r, -52.0, 0.0, axonRgb(150.0, 100.0, 56.0), axonRgb(120.0, 80.0, 44.0));
        axonShape(base, axonRect(r, -17.0, -66.0, 34.0, 20.0, 4.0), px, r, -66.0, -46.0, axonRgb(200.0, 206.0, 216.0), axonRgb(86.0, 94.0, 108.0));
    } else if (tool == 3) {
        // szlifierka: tarcza z obracającymi się ziarnami
        axonBlend(base, vec3(0.0), 0.27 * axonCover(length(q * vec2(1.0, 1.1) - vec2(0.0, 3.0)) - 21.0, px));
        axonBlend(base, axonRgb(40.0, 44.0, 52.0), axonCover(length(q) - 20.0, px));
        float spin = axonClock * AXON_TAU / 40.0 * (on ? 12.0 : 1.0);
        float sector = AXON_TAU / 12.0;
        float a = atan(q.y, q.x) - spin;
        float am = mod(a + sector * 0.5, sector) - sector * 0.5;
        axonBlend(base, axonRgb(190.0, 120.0, 70.0), axonCover(length(vec2(length(q) * am, length(q) - 17.0)) - 2.2, px));
        axonBlend(base, axonRgb(150.0, 158.0, 170.0), axonCover(length(q) - 8.0, px));
        if (on) axonSparks(base, p, cursor + vec2(14.0, 12.0), 1.2, axonRgb(255.0, 210.0, 120.0), px);
    } else if (tool == 4) {
        // strug i wióry
        axonShape(base, axonRect(q, -8.0, -28.0, 36.0, 32.0, 5.0), px, q, -28.0, 4.0, axonRgb(230.0, 160.0, 70.0), axonRgb(150.0, 90.0, 36.0));
        axonBlend(base, axonRgb(190.0, 196.0, 206.0), axonCover(axonRect(q, -12.0, 4.0, 44.0, 7.0, 2.0), px));
        axonBlend(base, axonRgb(120.0, 70.0, 30.0), axonCover(axonRect(q, 8.0, -42.0, 7.0, 16.0, 3.0), px));
        if (on) {
            for (int i = 0; i < 4; i++) {
                float a = axonClock * AXON_TAU / 40.0 * 3.0 + float(i);
                vec2 c = vec2(20.0 + cos(a) * 9.0 + float(i) * 4.0, 8.0 - abs(sin(a)) * 12.0);
                axonBlend(base, axonRgb(236.0, 206.0, 150.0), axonCover(length(q - c) - 2.4, px));
            }
        }
    } else if (tool == 5) {
        // gąbka i bąbelki
        vec2 r = axonRot(q, -12.0);
        axonShape(base, axonRect(r, -22.0, -14.0, 44.0, 28.0, 8.0), px, r, -14.0, 14.0, axonRgb(255.0, 220.0, 90.0), axonRgb(200.0, 150.0, 30.0));
        axonBlend(base, axonRgb(90.0, 160.0, 90.0), axonCover(axonRect(r, -22.0, -14.0, 44.0, 8.0, 4.0), px));
        if (on) {
            float seed = floor(axonClock * 0.4);
            for (int i = 0; i < 6; i++) {
                vec2 c = vec2((axonHash(seed * 3.1 + float(i) * 1.7) - 0.5) * 46.0, (axonHash(seed * 4.3 + float(i) * 2.9) - 0.5) * 36.0);
                float rad = 3.0 + axonHash(seed * 7.7 + float(i)) * 4.0;
                axonBlend(base, axonRgb(200.0, 235.0, 255.0), 0.8 * axonCover(abs(length(q - c) - rad) - 0.6, px));
            }
        }
    } else if (tool == 6) {
        // palnik spawalniczy: przy spawaniu niebieska poświata, punkt i iskry
        if (on) {
            axonGlow(base, p, cursor, 34.0, axonRgb(150.0, 200.0, 255.0), 0.55);
            axonBlend(base, vec3(1.0), axonCover(length(q) - 5.0, px));
            axonSparks(base, p, cursor, 1.5, axonRgb(255.0, 200.0, 110.0), px);
        }
        vec2 r = axonRot(q, 35.0);
        axonShape(base, axonRect(r, -4.0, -60.0, 8.0, 54.0, 3.0), px, r, -60.0, -6.0, axonRgb(120.0, 128.0, 140.0), axonRgb(60.0, 66.0, 76.0));
        axonBlend(base, axonRgb(200.0, 206.0, 216.0), axonCover(axonRect(r, -3.0, -8.0, 6.0, 10.0, 2.0), px));
    } else if (tool == 7) {
        // wiertarka: drży i kręci gwintem przy wierceniu
        vec2 r = q - vec2(on ? sin(axonClock * AXON_TAU / 40.0 * 19.0) * 1.2 : 0.0, 0.0);
        float body = axonRect(r, -5.0, -64.0, 10.0, 58.0, 3.0);
        axonShape(base, body, px, r, -64.0, -6.0, axonRgb(170.0, 176.0, 188.0), axonRgb(80.0, 86.0, 98.0));
        float scroll = on ? axonClock * 2.0 : 0.0;
        float yy = mod(r.y + 6.0 - scroll, 4.0) - 2.0;
        float thread = max(abs(yy - r.x * 0.3) - 0.5, max(abs(r.x) - 5.0, max(r.y + 6.0, -22.0 - r.y)));
        axonBlend(base, axonRgb(40.0, 44.0, 52.0), axonCover(thread, px));
        if (on) axonSparks(base, p, cursor, 1.0, axonRgb(255.0, 214.0, 140.0), px);
    } else if (tool == 8) {
        // frez: tarcza z czterema ostrzami
        axonBlend(base, vec3(0.0), 0.27 * axonCover(length(q * vec2(1.0, 1.1) - vec2(0.0, 3.0)) - 13.0, px));
        axonBlend(base, axonRgb(60.0, 66.0, 78.0), axonCover(length(q) - 13.0, px));
        float spin = axonClock * AXON_TAU / 40.0 * (on ? 16.0 : 1.0);
        for (int i = 0; i < 4; i++) {
            float a = spin + float(i) * AXON_TAU / 4.0;
            axonBlend(base, axonRgb(210.0, 216.0, 226.0), axonCover(axonSegment(q, vec2(0.0), vec2(cos(a), sin(a)) * 12.0) - 1.7, px));
        }
        axonBlend(base, axonRgb(30.0, 32.0, 38.0), axonCover(length(q) - 3.0, px));
        if (on) axonSparks(base, p, cursor, 0.8, axonRgb(255.0, 214.0, 140.0), px);
    }
}

void axonSprite(inout vec3 base, vec2 p, float px, vec2 cursor, int i) {
    vec4 a = axonSpriteA[i];
    vec4 b = axonSpriteB[i];
    int kind = int(b.x + 0.5);
    if (kind == 0) {
        return;
    }
    float dt = mod(axonClock - b.w, AXON_CLOCK_PERIOD);
    vec2 lim = (((i & 1) == 0) ? axonSpriteLimP[i >> 1].xy : axonSpriteLimP[i >> 1].zw);
    vec2 pos = a.xy;
    if (kind != 5) {
        pos += a.zw * dt;
    }
    float heat = 0.0;
    if (lim.y > lim.x) {
        pos.x = clamp(pos.x, lim.x, lim.y);
        heat = (pos.x - lim.x) / (lim.y - lim.x);
    }
    float size = b.z;
    int colorIndex = int(b.y + 0.5);
    vec3 color = axonEffectColor(colorIndex, heat);

    if (kind == 1) {
        // Znacznik skali: pos.y to czubek trójkąta, size to długość trzonka.
        if (abs(p.x - pos.x) > 30.0) return;
        axonGlow(base, p, vec2(pos.x, pos.y + size * 0.5), 26.0, color, 0.35);
        float stem = (1.5 - abs(p.x - pos.x)) / px;
        float stemY = min(p.y - pos.y, pos.y + size - p.y) / px;
        axonBlend(base, color, clamp(stem + 0.5, 0.0, 1.0) * clamp(stemY + 0.5, 0.0, 1.0));
        float u = (p.y - (pos.y - 12.0)) / 12.0;
        float half_ = 8.0 * (1.0 - u);
        float inside = (half_ - abs(p.x - pos.x)) * 0.83 / px;
        float cover = clamp(inside + 0.5, 0.0, 1.0) * clamp(min(u, 1.0 - u) * 12.0 / px + 0.5, 0.0, 1.0);
        axonBlend(base, color, cover);
    } else if (kind == 2) {
        // Rozżarzony pręt od lim.x do lim.y, wysokość 2 * size, kolor zależy od temperatury.
        float cx = (lim.x + lim.y) * 0.5;
        float halfW = (lim.y - lim.x) * 0.5;
        float halfH = size;
        axonGlow(base, p, vec2(cx, pos.y), 150.0, color, min(0.5, heat * 0.6));
        vec2 q = abs(p - vec2(cx, pos.y)) - vec2(halfW - 10.0, halfH - 10.0);
        float dist = length(max(q, 0.0)) + min(max(q.x, q.y), 0.0) - 10.0;
        float shade = mix(1.3, 0.7, clamp((p.y - (pos.y - halfH)) / (2.0 * halfH), 0.0, 1.0));
        float body = axonCover(dist, px);
        axonBlend(base, clamp(color * shade, 0.0, 1.0), body);
        axonBlend(base, vec3(1.0), 0.2 * axonCover(abs(dist + 0.6) - 0.6, px) * body);
    } else if (kind == 3) {
        // Płomienie pod prętem: 9 języków między lim.x + 30 a lim.y - 30, baza na pos.y.
        if (p.y > pos.y + 2.0 || p.y < pos.y - 44.0) return;
        float first = lim.x + 30.0;
        float step_ = (lim.y - lim.x - 60.0) / 8.0;
        float j = clamp(floor((p.x - first) / step_ + 0.5), 0.0, 8.0);
        float fx = first + j * step_;
        float h = 26.0 + 14.0 * sin(axonClock * AXON_TAU * 4.0 / AXON_CLOCK_PERIOD + j * 1.7);
        float u = (pos.y - p.y) / h;
        float w = 9.0 * (1.0 - u * u);
        float inside = (w - abs(p.x - fx)) / px;
        float cover = clamp(inside + 0.5, 0.0, 1.0) * clamp(u * h / px + 0.5, 0.0, 1.0) * clamp((1.0 - u) * h / px + 0.5, 0.0, 1.0);
        vec3 flame = mix(axonRgb(255.0, 90.0, 20.0), axonRgb(255.0, 230.0, 120.0), clamp(u, 0.0, 1.0));
        axonBlend(base, flame, 0.9 * cover);
    } else if (kind == 4) {
        // Pulsujący cel: poświata i pierścień, które oddychają 1,5 razy na sekundę.
        float d = length(p - pos);
        if (d > size * 2.6 + 4.0) return;
        float pulse = 0.5 + 0.5 * sin(axonClock * AXON_TAU * 3.0 / AXON_CLOCK_PERIOD);
        axonGlow(base, p, pos, size * 2.4, color, 0.3 + 0.2 * pulse);
        axonBlend(base, color, 0.8 * axonCover(abs(d - (size + 3.0 + pulse * 3.0)) - 1.0, px));
    } else if (kind == 5) {
        // Narzędzie przy kursorze: rysowane tam, gdzie celuje gracz, bez opóźnienia serwera.
        axonTool(base, p, px, cursor, int(size + 0.5), lim.x > 0.5, color, a.xy);
    } else if (kind == 6) {
        // Siatka celownika optyki z łukiem przytrzymania (lo = procent).
        vec2 q = p - pos;
        if (length(q) > 40.0) return;
        float ring = abs(length(q) - 18.0) - 0.8;
        float cross_ = min(
            max(abs(q.y) - 0.8, abs(abs(q.x) - 21.0) - 13.0),
            max(abs(q.x) - 0.8, abs(abs(q.y) - 21.0) - 13.0));
        axonBlend(base, color, axonCover(min(ring, cross_), px));
        float frac = lim.x / 100.0;
        float ang = mod(atan(q.x, -q.y), AXON_TAU) / AXON_TAU;
        if (ang <= frac) {
            axonBlend(base, axonEffectColor(1, 0.0), axonCover(abs(length(q) - 24.0) - 1.7, px));
        }
    } else if (kind == 7) {
        // Ruchomy cel optyki: poświata, dwa pierścienie i czerwony środek (size = tolerancja).
        float d = length(p - pos);
        if (d > size * 2.6) return;
        vec3 green = axonEffectColor(1, 0.0);
        axonGlow(base, p, pos, size * 2.5, green, 0.28);
        axonBlend(base, green, 0.9 * axonCover(abs(d - size) - 1.0, px));
        axonBlend(base, green, 0.5 * axonCover(abs(d - size * 0.55) - 0.7, px));
        axonBlend(base, axonEffectColor(2, 0.0), axonCover(d - 4.0, px));
    }
}

// Piksel obrazu mapy bez znacznika i tabeli sprite'ów (zastąpione sąsiednim wierszem).
vec3 axonTexel(ivec2 pixel) {
    pixel = clamp(pixel, ivec2(0), ivec2(127));
    int markerWidth = axonDensity > 1 ? 32 : 24;
    if (pixel.y == 0 && pixel.x < markerWidth) {
        pixel.y = 1;
    } else if (pixel.y == 127) {
        // znacznik (x < 8) i tabela sprite'ów (reszta wiersza) nie są obrazem
        pixel.y = 126;
    }
    return texelFetch(Sampler0, pixel, 0).rgb;
}

// Ostre skalowanie z wygładzonymi krawędziami: wewnątrz piksela obrazu kolor jest stały, a przejście
// do sąsiada trwa jeden piksel ekranu. Przy niecałkowitej skali (np. 1280 px obrazu na 1920 px ekranu)
// piksele nie są nierówne, a przy całkowitej obraz jest tak ostry jak przy texelFetch.
vec3 axonSharp(vec2 uv) {
    vec2 texel = uv * 128.0;
    vec2 perScreen = max(fwidth(texel), vec2(1e-4));
    vec2 scale = max(1.0 / perScreen, vec2(1.0));
    vec2 base = floor(texel);
    vec2 inside = texel - base - 0.5;
    vec2 range = 0.5 - 0.5 / scale;
    vec2 f = (inside - clamp(inside, -range, range)) * scale;
    vec2 p = base + 0.5 + f - 0.5;
    ivec2 i = ivec2(floor(p));
    vec2 w = fract(p);
    vec3 c00 = axonTexel(i);
    vec3 c10 = axonTexel(i + ivec2(1, 0));
    vec3 c01 = axonTexel(i + ivec2(0, 1));
    vec3 c11 = axonTexel(i + ivec2(1, 1));
    return mix(mix(c00, c10, w.x), mix(c01, c11, w.x), w.y);
}

// ---------------------------------------------------------------- panel HUD (AxonScoreboard)
const float AXON_HUD_ALPHA[5] = float[5](0.94, 0.8, 0.62, 0.42, 0.22);

float axonRoundBox(vec2 p, vec2 hsize, float r) {
    vec2 q = abs(p) - hsize + r;
    return length(max(q, 0.0)) + min(max(q.x, q.y), 0.0) - r;
}

vec3 axonHudAccent(float x) {
    // skiny Elity (alfa 254 w akcencie 2): akcent przelewa się w drugi kolor i przesuwa się po nim błysk
    if (axonHudAcc2.a > 0.999) {
        return axonHudAcc;
    }
    float t = GameTime * 24000.0 / 20.0;
    float wave = 0.5 + 0.5 * sin(t * 1.3 - x * 0.05);
    return mix(axonHudAcc, axonHudAcc2.rgb, wave * 0.6);
}

vec4 axonHudBackground() {
    vec2 size = axonHudBox.xy;
    vec2 p = axonHudLocal;
    float aa = max(fwidth(p.x), 1e-3);
    float d = axonRoundBox(p - size * 0.5, size * 0.5, 4.0);
    // cień pod panelem (miękki, lekko w dół)
    float ds = axonRoundBox(p - size * 0.5 - vec2(0.0, 1.5), size * 0.5, 5.0);
    vec4 shadow = vec4(0.0, 0.0, 0.0, 0.32 * (1.0 - smoothstep(-1.0, 5.0, ds)));
    if (axonHudBox.w > 0.5) {
        // poświata alarmu zamiast cienia
        float pulse = 0.5 + 0.5 * sin(GameTime * 24000.0 * 0.26);
        shadow = vec4(1.0, 0.2, 0.15, (0.25 + 0.3 * pulse) * (1.0 - smoothstep(0.0, 7.0, d)));
    }
    float inside = 1.0 - smoothstep(-aa, aa, d);
    if (inside <= 0.0) {
        return shadow;
    }
    float alpha = AXON_HUD_ALPHA[int(clamp(axonHudBox.z, 0.0, 4.0))];
    vec3 col;
    if (p.y < 16.0) {
        col = mix(axonHudHead * 1.18, axonHudHead, p.y / 16.0);
        alpha = max(alpha, 0.5);
    } else {
        col = mix(axonHudBg * 1.12, axonHudBg, clamp((p.y - 16.0) / 40.0, 0.0, 1.0));
    }
    // jasna obwódka 1 px przy krawędzi
    col = mix(col, col + vec3(0.09), 1.0 - smoothstep(0.0, 1.2, -d));
    vec3 acc = axonHudAccent(p.x);
    // linia pod nagłówkiem: od akcentu do przezroczystej
    if (p.y >= 15.0 && p.y < 16.0) {
        float f = 1.0 - clamp(p.x / size.x, 0.0, 1.0) * 0.8;
        col = mix(col, acc, 0.9 * f);
        alpha = max(alpha, 0.9);
    }
    // pasek akcentu z lewej, pod nagłówkiem
    if (p.x >= 0.0 && p.x < 2.0 && p.y >= 16.0 && p.y < size.y - 4.0) {
        col = acc;
        alpha = 1.0;
    }
    vec4 panel = vec4(col, alpha * inside);
    if (axonHudBox.w > 0.5) {
        // alarm (rajd, atak): czerwona obwódka pulsuje
        float pulse = 0.5 + 0.5 * sin(GameTime * 24000.0 * 0.26);
        float rim = 1.0 - smoothstep(0.0, 1.6, -d);
        panel.rgb = mix(panel.rgb, vec3(1.0, 0.25, 0.22), rim * (0.55 + 0.45 * pulse));
        panel.a = max(panel.a, rim * inside);
    }
    // panel nad cieniem
    float a = panel.a + shadow.a * (1.0 - panel.a);
    return vec4((panel.rgb * panel.a + shadow.rgb * shadow.a * (1.0 - panel.a)) / max(a, 1e-4), a);
}

// Pasek 30 × 6: tor, wypełnienie z gradientem, przesuwający się błysk i lekka poświata.
vec4 axonHudBar() {
    vec2 p = axonHudLocal;
    float aa = max(fwidth(p.x), 1e-3);
    vec3 col = axonHudExtra.rgb;
    float f = axonHudExtra.a;
    float d = axonRoundBox(p - vec2(15.0, 3.0), vec2(15.0, 3.0), 3.0);
    float inside = 1.0 - smoothstep(-aa, aa, d);
    vec4 glow = vec4(col, 0.18 * f * (1.0 - smoothstep(0.0, 2.0, d)));
    if (inside <= 0.0) {
        return glow;
    }
    vec3 track = mix(vec3(0.0), col, 0.18);
    vec3 c = track;
    float a = 0.75;
    float fx = f * 30.0;
    if (p.x < fx) {
        c = mix(col * 1.25, col * 0.7, clamp(p.y / 6.0, 0.0, 1.0));
        float t = GameTime * 24000.0;
        float band = mod(t * 0.9, 70.0) - 20.0;
        c += vec3(0.35) * (1.0 - smoothstep(0.0, 5.0, abs(p.x - band - p.y)));
        // jaśniejszy koniec wypełnienia
        c += vec3(0.25) * (1.0 - smoothstep(0.0, 1.5, fx - p.x));
        a = 1.0;
    }
    return vec4(c, a * inside);
}

// Powiadomienie: zaokrąglone tło w kolorze skinu z barwną poświatą od krawędzi.
vec4 axonHudToast() {
    vec2 size = axonHudBox.xy;
    vec2 p = axonHudLocal;
    float aa = max(fwidth(p.x), 1e-3);
    float d = axonRoundBox(p - size * 0.5, size * 0.5, 4.0);
    float ds = axonRoundBox(p - size * 0.5 - vec2(0.0, 1.5), size * 0.5, 5.0);
    vec4 shadow = vec4(0.0, 0.0, 0.0, 0.3 * (1.0 - smoothstep(-1.0, 5.0, ds)));
    float inside = 1.0 - smoothstep(-aa, aa, d);
    if (inside <= 0.0) {
        return shadow;
    }
    vec3 col = axonHudExtra.rgb;
    vec3 c = mix(axonHudHead, axonHudBg, clamp(p.y / 16.0, 0.0, 1.0));
    c = mix(c, col, 0.22 * (1.0 - clamp(p.x / max(size.x, 1.0), 0.0, 1.0)));
    c = mix(c, col, 0.7 * (1.0 - smoothstep(0.0, 1.2, -d)));
    vec4 panel = vec4(c, 0.93 * inside);
    float a = panel.a + shadow.a * (1.0 - panel.a);
    return vec4((panel.rgb * panel.a + shadow.rgb * shadow.a * (1.0 - panel.a)) / max(a, 1e-4), a);
}

// Pionowy pasek czasu powiadomienia (opada w miarę upływu czasu, liczony z zegara gry).
vec4 axonHudTimer() {
    vec2 p = axonHudLocal;
    float left = axonHudExtra.a;
    if (axonHudBox.z > 250.0) {
        discard;
    }
    float filled = 16.0 * (1.0 - left);
    vec3 c = p.y >= filled ? axonHudExtra.rgb * 1.1 : axonHudExtra.rgb * 0.25;
    // na starcie błysk
    float flash = 1.0 - clamp(axonHudBox.z / 6.0, 0.0, 1.0);
    return vec4(c + vec3(flash * 0.6), 0.95);
}

// Tło banera: ciemny pas z rozchodzącymi się od środka liniami akcentu; pojawia się i gaśnie z zegarem gry.
vec4 axonHudBanner() {
    float age = axonHudBox.z;
    float w = axonHudBox.x;
    float life = clamp(age / 6.0, 0.0, 1.0) * (1.0 - clamp((age - 70.0) / 10.0, 0.0, 1.0));
    if (age > 80.0 || life <= 0.0) {
        discard;
    }
    vec2 p = axonHudLocal;
    float hw = w * 0.5 + 40.0;
    float edge = 1.0 - smoothstep(hw * 0.45, hw, abs(p.x));
    float vy = 1.0 - smoothstep(10.0, 23.0, abs(p.y - 9.0));
    vec3 acc = axonHudAccent(p.x + hw);
    vec4 band = vec4(mix(axonHudBg, acc, 0.12), 0.72 * edge * vy);
    float spread = clamp(age / 12.0, 0.0, 1.0) * hw;
    float line = (1.0 - smoothstep(0.0, 1.0, abs(abs(p.y - 9.0) - 13.0))) * (1.0 - smoothstep(spread * 0.6, spread, abs(p.x)));
    vec4 l = vec4(acc * 1.2, line);
    vec4 o = vec4(mix(band.rgb, l.rgb, l.a), max(band.a, l.a));
    o.a *= life;
    return o;
}

const float AXON_MINI_RANGE[4] = float[4](32.0, 64.0, 96.0, 128.0);
const float AXON_MINI_PAD_F = 0.07;
// ── Minimapa AxonMap (opis w rendertype_text.vsh) ───────────────────────────────────────────────
// Odległość od brzegu mapy (ujemna w środku), w jednostkach połowy boku. Kwadrat ma zaokrąglone rogi.
float axonMiniEdge(vec2 l, int s) {
    if (((s >> 6) & 1) == 1) {
        return length(l) - 1.0;
    }
    vec2 q = abs(l) - vec2(1.0 - 0.08);
    return length(max(q, 0.0)) + min(max(q.x, q.y), 0.0) - 0.08;
}

bool axonMiniOutside(vec2 l, int s, float grow) {
    return axonMiniEdge(l, s) > grow;
}

vec4 axonMiniTile() {
    vec2 l = axonMiniL;
    int s = int(axonMiniA.w + 0.5);
    if (axonMiniOutside(l, s, 0.0)) {
        return vec4(0.0);
    }
    float range = AXON_MINI_RANGE[(s >> 4) & 3];
    vec2 f = axonMiniB.zw;
    vec2 r = vec2(-f.y, f.x);
    // cztery próbki na piksel: przy oddaleniu teren nie migocze
    vec2 dl = vec2(dFdx(l.x), dFdy(l.y)) * 0.25;
    vec4 acc = vec4(0.0);
    for (int i = 0; i < 4; i++) {
        vec2 ll = l + vec2(i == 0 || i == 2 ? -dl.x : dl.x, i < 2 ? -dl.y : dl.y);
        vec2 off = ((s >> 7) & 1) == 1 ? (r * ll.x - f * ll.y) * range : ll * range;
        vec2 t = axonMiniA.xy + off;
        if (t.x < 0.0 || t.y < 0.0 || t.x >= 128.0 || t.y >= 128.0) {
            continue;
        }
        vec4 c = texelFetch(Sampler0, ivec2(axonMiniB.xy + floor(t)), 0);
        if (c.a > 0.5) {
            acc += vec4(c.rgb, 1.0);
        }
    }
    if (acc.a < 0.5) {
        return vec4(0.0);
    }
    // kolory mapy vanilli są przygaszone: trochę więcej nasycenia i jasności
    vec3 c = acc.rgb / acc.a;
    float g = dot(c, vec3(0.299, 0.587, 0.114));
    c = clamp(mix(vec3(g), c, 1.18) * 1.06, 0.0, 1.0);
    return vec4(c, 1.0);
}

// Litera N (wysokość 1.2, szerokość 1.0) jako trzy kreski; zwraca odległość od kreski.
float axonMiniSeg(vec2 p, vec2 a, vec2 b) {
    vec2 pa = p - a;
    vec2 ba = b - a;
    return length(pa - ba * clamp(dot(pa, ba) / dot(ba, ba), 0.0, 1.0));
}

float axonMiniLetterN(vec2 p) {
    float d = axonMiniSeg(p, vec2(-0.45, 0.6), vec2(-0.45, -0.6));
    d = min(d, axonMiniSeg(p, vec2(-0.45, -0.6), vec2(0.45, 0.6)));
    return min(d, axonMiniSeg(p, vec2(0.45, 0.6), vec2(0.45, -0.6)));
}

// Strzałka gracza w układzie (bok, przód): ujemna w środku.
float axonMiniArrow(vec2 a) {
    return max(abs(a.x) * 1.3 + a.y - 1.0, -a.y - 0.7 - abs(a.x) * 0.45);
}

vec4 axonMiniOver(vec4 top, vec4 under) {
    float a = top.a + under.a * (1.0 - top.a);
    return a < 1e-4 ? vec4(0.0) : vec4((top.rgb * top.a + under.rgb * under.a * (1.0 - top.a)) / a, a);
}

vec4 axonMiniFrame(bool front) {
    vec2 l = axonMiniL;
    int s = int(axonMiniA.w + 0.5);
    bool rot = ((s >> 7) & 1) == 1;
    vec2 f = axonMiniB.zw;
    vec2 r = vec2(-f.y, f.x);
    float px = max(fwidth(l.x), 1e-4);
    float d = axonMiniEdge(l, s);
    float pad = AXON_MINI_PAD_F;
    if (!front) {
        float outer = 1.0 - smoothstep(pad - 1.5 * px, pad - 0.5 * px, d);
        if (outer <= 0.0) {
            return vec4(0.0);
        }
        if (d < 0.0) {
            // nieznany teren: ciemne tło w delikatne ukośne paski
            float stripe = step(0.5, fract((l.x + l.y) * 9.0));
            return vec4(mix(vec3(0.075, 0.085, 0.105), vec3(0.095, 0.105, 0.125), stripe), 0.94);
        }
        // obwódka: ciemny pas z jaśniejszą górą, złota linia na zewnątrz, czarna przy mapie
        vec3 band = mix(vec3(0.17, 0.18, 0.22), vec3(0.09, 0.10, 0.12), clamp(l.y * 0.5 + 0.5, 0.0, 1.0));
        float gold = smoothstep(pad - 3.0 * px, pad - 2.0 * px, d) * (1.0 - smoothstep(pad - 1.6 * px, pad - 0.8 * px, d));
        vec3 col = mix(band, vec3(0.86, 0.69, 0.33), gold);
        col = mix(vec3(0.02, 0.02, 0.03), col, smoothstep(0.6 * px, 1.6 * px, d));
        return vec4(col, outer);
    }
    vec4 o = vec4(0.0);
    // cień wewnętrzny przy brzegu mapy
    if (d < 0.0) {
        o = vec4(0.0, 0.0, 0.0, 0.32 * (1.0 - smoothstep(0.0, 0.09, -d)));
    }
    // gracz: strzałka z cieniem (przy obrocie zawsze w górę)
    vec2 dir = rot ? vec2(0.0, -1.0) : vec2(f.x, f.y);
    vec2 side = vec2(-dir.y, dir.x);
    float k = 0.085;
    vec2 a = vec2(dot(l, side), dot(l, dir)) / k;
    vec2 sh = l - vec2(0.012, 0.02);
    vec2 as = vec2(dot(sh, side), dot(sh, dir)) / k;
    float apx = px / k;
    float ds = axonMiniArrow(as);
    o = axonMiniOver(vec4(0.0, 0.0, 0.0, 0.45 * (1.0 - smoothstep(-apx, apx * 2.0, ds))), o);
    float da = axonMiniArrow(a);
    float body = 1.0 - smoothstep(-apx, apx, da + 0.22);
    float rim = 1.0 - smoothstep(-apx, apx, da);
    vec3 ac = mix(vec3(0.05, 0.06, 0.08), mix(vec3(0.82, 0.86, 0.92), vec3(1.0), step(0.0, dot(a, vec2(1.0, 0.0)))), body);
    o = axonMiniOver(vec4(ac, rim), o);
    // północ: czerwone kółko z literą N na obwódce
    vec2 n = rot ? vec2(dot(vec2(0.0, -1.0), r), -dot(vec2(0.0, -1.0), f)) : vec2(0.0, -1.0);
    vec2 np;
    if (((s >> 6) & 1) == 1 || rot) {
        np = normalize(n) * (1.0 + pad * 0.5);
    } else {
        np = vec2(0.0, -1.0 - pad * 0.5);
    }
    float nr = 0.085;
    vec2 q = (l - np) / nr;
    float qpx = px / nr;
    float disk = 1.0 - smoothstep(1.0 - qpx, 1.0 + qpx, length(q));
    if (disk > 0.0) {
        float ring = smoothstep(0.78 - qpx, 0.78 + qpx, length(q));
        vec3 dc = mix(vec3(0.85, 0.2, 0.18), vec3(0.08, 0.06, 0.06), ring);
        float letter = 1.0 - smoothstep(0.11 - qpx, 0.11 + qpx, axonMiniLetterN(q * 1.55));
        dc = mix(dc, vec3(1.0), letter);
        o = axonMiniOver(vec4(dc, disk), o);
    }
    return o;
}

const vec3 AXON_MINI_PINS[8] = vec3[8](vec3(1.0, 0.58, 0.18), vec3(0.32, 0.86, 1.0), vec3(0.93, 0.91, 0.86),
        vec3(0.36, 0.9, 0.5), vec3(0.38, 0.58, 1.0), vec3(0.95, 0.27, 0.25), vec3(1.0, 0.84, 0.26), vec3(0.8, 0.52, 1.0));

// Kształt znacznika (ujemny w środku): działka = zaokrąglony kwadrat, członek działki = kółko,
// struktura = romb, punkt = pinezka, śmierć = krzyżyk.
float axonMiniPinShape(vec2 l, int type) {
    if (type == 5) {
        float x = min(abs(l.x - l.y), abs(l.x + l.y)) * 0.7071 - 0.13;
        return max(x, length(l) - 0.62);
    }
    if (type == 0) {
        vec2 q = abs(l) - vec2(0.38);
        return length(max(q, 0.0)) + min(max(q.x, q.y), 0.0) - 0.12;
    }
    if (type == 1) {
        return length(l) - 0.5;
    }
    if (type == 2 || type == 3) {
        return (abs(l.x) + abs(l.y)) * 0.7071 - 0.42;
    }
    // pinezka: kółko u góry i szpic w dół
    vec2 c = l - vec2(0.0, -0.22);
    float circle = length(c) - 0.42;
    float h = clamp((l.y + 0.22) / 1.0, 0.0, 1.0);
    float cone = max(abs(l.x) - 0.42 * (1.0 - h) * 0.95, max(-0.22 - l.y, l.y - 0.78));
    return min(circle, cone);
}

// Znacznik w układzie l (-1..1 to rozmiar znacznika); grot zamiast znacznika, gdy cel jest poza mapą lub kompasem.
vec4 axonPinAt(vec2 l, int type, bool far, vec2 dir, float px) {
    vec3 c = AXON_MINI_PINS[type];
    if (far) {
        vec2 a = vec2(dot(l, vec2(-dir.y, dir.x)), dot(l, dir)) / 0.7;
        float apx = px / 0.7;
        float t = max(abs(a.x) * 1.9 + a.y - 0.8, -a.y - 0.6);
        float ts = max(abs(a.x) * 1.9 + a.y - 0.8, -a.y - 0.6) - 0.22;
        float fill = 1.0 - smoothstep(-apx, apx, t + 0.2);
        float rim = 1.0 - smoothstep(-apx, apx, ts);
        return vec4(mix(vec3(0.05), c, fill), rim * 0.9);
    }
    float d = axonMiniPinShape(l, type);
    float ds = axonMiniPinShape(l - vec2(0.07, 0.11), type);
    vec4 o = vec4(0.0, 0.0, 0.0, 0.4 * (1.0 - smoothstep(0.0, 0.2, ds)));
    float rim = 1.0 - smoothstep(0.14 - px, 0.14 + px, d);
    float fill = 1.0 - smoothstep(-px, px, d);
    // lekki połysk u góry wypełnienia
    vec3 fc = c * (1.0 + 0.18 * clamp(-l.y, 0.0, 1.0));
    if (type >= 4 && type != 5) {
        // biała kropka w główce pinezki
        float dot_ = 1.0 - smoothstep(0.15 - px, 0.15 + px, length(l - vec2(0.0, -0.22)));
        fc = mix(fc, vec3(1.0), dot_);
    }
    vec4 shape = vec4(mix(vec3(0.05, 0.05, 0.06), fc, fill), rim);
    return axonMiniOver(shape, o);
}

vec4 axonMiniPin() {
    vec2 l = axonMiniL;
    int type = int(fract(axonMiniA.z) * 16.0 + 0.5) & 7;
    float px = max(fwidth(l.x), 1e-3);
    return axonPinAt(l, type, axonMiniB.x > 0.5, vec2(cos(axonMiniB.y), sin(axonMiniB.y)), px);
}

// ── Kompas AxonMap (opis w rendertype_text.vsh) ─────────────────────────────────────────────────
// Czcionka 5 × 7: 0–9, N, E, S, W, m, k, kropka, stopień. Wiersz = 5 bitów, bit 4 to lewa kolumna.
const int AXON_FONT[126] = int[126](
    14, 17, 19, 21, 25, 17, 14,     4, 12, 4, 4, 4, 4, 14,          14, 17, 1, 2, 4, 8, 31,
    31, 2, 4, 2, 1, 17, 14,         2, 6, 10, 18, 31, 2, 2,         31, 16, 30, 1, 1, 17, 14,
    6, 8, 16, 30, 17, 17, 14,       31, 1, 2, 4, 8, 8, 8,           14, 17, 17, 14, 17, 17, 14,
    14, 17, 17, 15, 1, 2, 12,       17, 25, 21, 19, 17, 17, 17,     31, 16, 16, 30, 16, 16, 31,
    15, 16, 16, 14, 1, 1, 30,       17, 17, 17, 21, 21, 21, 10,     0, 0, 26, 21, 21, 17, 17,
    16, 16, 18, 20, 24, 20, 18,     0, 0, 0, 0, 0, 12, 12,          12, 18, 18, 12, 0, 0, 0);
#define AXON_CH_N 10
#define AXON_CH_E 11
#define AXON_CH_S 12
#define AXON_CH_W 13
#define AXON_CH_M 14
#define AXON_CH_K 15
#define AXON_CH_DOT 16
#define AXON_CH_DEG 17

// Pokrycie piksela przez znak (lewy górny róg w origin, piksel czcionki gp): 4 próbki, więc znak przesuwa się gładko.
float axonGlyph(vec2 p, vec2 origin, float gp, int ch) {
    float acc = 0.0;
    for (int i = 0; i < 4; i++) {
        vec2 o = vec2(i == 0 || i == 2 ? -0.25 : 0.25, i < 2 ? -0.25 : 0.25);
        vec2 g = (p + o - origin) / gp;
        if (g.x < 0.0 || g.y < 0.0 || g.x >= 5.0 || g.y >= 7.0) {
            continue;
        }
        ivec2 cell = ivec2(floor(g));
        acc += float((AXON_FONT[ch * 7 + cell.y] >> (4 - cell.x)) & 1);
    }
    return acc * 0.25;
}

// Napis do 5 znaków wyśrodkowany na cx, górą na y.
float axonText(vec2 p, float cx, float y, float gp, int n, int c0, int c1, int c2, int c3, int c4) {
    float w = float(n) * 6.0 * gp - gp;
    float x0 = cx - w * 0.5;
    int i = int(floor((p.x - x0) / (6.0 * gp)));
    float best = 0.0;
    // próbki mogą wejść w sąsiedni znak, więc sprawdzamy też obok
    for (int k = -1; k <= 1; k++) {
        int j = i + k;
        if (j < 0 || j >= n) {
            continue;
        }
        int ch = j == 0 ? c0 : j == 1 ? c1 : j == 2 ? c2 : j == 3 ? c3 : c4;
        best = max(best, axonGlyph(p, vec2(x0 + float(j) * 6.0 * gp, y), gp, ch));
    }
    return best;
}

// Odległość jako 12m, 345m, 1.2k, 15k.
float axonDistanceText(vec2 p, float cx, float y, float gp, float dist) {
    if (dist < 999.5) {
        int m = int(dist + 0.5);
        if (m < 10) {
            return axonText(p, cx, y, gp, 2, m, AXON_CH_M, 0, 0, 0);
        }
        if (m < 100) {
            return axonText(p, cx, y, gp, 3, m / 10, m % 10, AXON_CH_M, 0, 0);
        }
        return axonText(p, cx, y, gp, 4, m / 100, (m / 10) % 10, m % 10, AXON_CH_M, 0);
    }
    if (dist < 9950.0) {
        int t = int(dist / 100.0 + 0.5);
        return axonText(p, cx, y, gp, 4, t / 10, AXON_CH_DOT, t % 10, AXON_CH_K, 0);
    }
    int k = min(int(dist / 1000.0 + 0.5), 99);
    return axonText(p, cx, y, gp, 3, k / 10, k % 10, AXON_CH_K, 0, 0);
}

const int AXON_DIRS[16] = int[16](AXON_CH_N, -1, AXON_CH_N, AXON_CH_E, AXON_CH_E, -1, AXON_CH_S, AXON_CH_E,
        AXON_CH_S, -1, AXON_CH_S, AXON_CH_W, AXON_CH_W, -1, AXON_CH_N, AXON_CH_W);

vec4 axonCompassBar() {
    vec2 p = axonMiniL;
    float heading = axonMiniA.x;
    float span = axonMiniA.y;
    float halfW = axonMiniB.x;
    float bh = axonMiniB.y;
    float gp = axonMiniB.z;
    float ppd = halfW / (span * 0.5);
    // końce paska gasną, środek jest pełny
    float fade = 1.0 - smoothstep(halfW * 0.72, halfW, abs(p.x));
    float r = floor(bh * 0.3);
    float d = axonRoundBox(p - vec2(0.0, bh * 0.5), vec2(halfW, bh * 0.5), r);
    float inside = 1.0 - smoothstep(-0.5, 0.5, d);
    vec3 band = mix(vec3(0.16, 0.17, 0.21), vec3(0.07, 0.08, 0.10), clamp(p.y / bh, 0.0, 1.0));
    vec4 o = vec4(band, 0.82 * inside * mix(0.15, 1.0, fade));
    // złota linia na dole paska
    float gold = step(bh - 1.5, p.y) * step(p.y, bh - 0.5) * step(abs(p.x), halfW - r);
    o = axonMiniOver(vec4(0.86, 0.69, 0.33, 0.9 * gold * fade), o);
    if (inside > 0.0) {
        float a = heading + p.x / ppd;
        // kreski co 5° (dłuższe co 15°), litery co 45°
        float t = a / 5.0;
        float idx = mod(floor(t + 0.5), 72.0);
        float dpx = abs(t - floor(t + 0.5)) * 5.0 * ppd;
        if (mod(idx, 9.0) > 0.5) {
            bool major = mod(idx, 3.0) < 0.5;
            float len = (major ? 0.3 : 0.16) * bh;
            float y1 = bh - 0.14 * bh;
            float cov = clamp(1.0 - dpx, 0.0, 1.0) * step(y1 - len, p.y) * step(p.y, y1);
            o = axonMiniOver(vec4(vec3(major ? 0.78 : 0.5), cov * fade), o);
        }
        float k = floor(a / 45.0 + 0.5);
        int dir = int(mod(k, 8.0));
        float lx = p.x + (k * 45.0 - a) * ppd;
        float cy = bh * 0.42;
        float cov;
        vec3 col;
        if ((dir & 1) == 0) {
            int ch = AXON_DIRS[dir * 2];
            cov = axonText(p, lx, cy - 3.5 * gp, gp, 1, ch, 0, 0, 0, 0);
            col = dir == 0 ? vec3(1.0, 0.33, 0.28) : vec3(1.0);
        } else {
            float g2 = gp * 0.75;
            cov = axonText(p, lx, cy - 3.5 * g2, g2, 2, AXON_DIRS[dir * 2], AXON_DIRS[dir * 2 + 1], 0, 0, 0);
            col = vec3(0.72, 0.74, 0.78);
        }
        o = axonMiniOver(vec4(col, cov * fade), o);
        // środek: złoty grot u góry
        float tri = max(abs(p.x) / (0.2 * bh) + p.y / (0.24 * bh) - 1.0, -p.y);
        o = axonMiniOver(vec4(0.95, 0.78, 0.38, 1.0 - smoothstep(-0.04, 0.04, tri)), o);
    }
    // okienko z kierunkiem w stopniach pod środkiem paska
    int deg = int(mod(floor(heading + 0.5), 360.0));
    int n = deg >= 100 ? 3 : deg >= 10 ? 2 : 1;
    float w = float(n + 1) * 6.0 * gp + 4.0 * gp;
    float y0 = bh + 2.0 * gp;
    float pill = axonRoundBox(p - vec2(0.0, y0 + 5.5 * gp), vec2(w * 0.5, 5.5 * gp), 2.0 * gp);
    float pc = 1.0 - smoothstep(-0.5, 0.5, pill);
    o = axonMiniOver(vec4(0.07, 0.08, 0.10, 0.8 * pc), o);
    float ty = y0 + 2.0 * gp;
    float tc = n == 3 ? axonText(p, 0.0, ty, gp, 4, deg / 100, (deg / 10) % 10, deg % 10, AXON_CH_DEG, 0)
            : n == 2 ? axonText(p, 0.0, ty, gp, 3, deg / 10, deg % 10, AXON_CH_DEG, 0, 0)
            : axonText(p, 0.0, ty, gp, 2, deg, AXON_CH_DEG, 0, 0, 0);
    o = axonMiniOver(vec4(vec3(0.95, 0.9, 0.78), tc), o);
    return o;
}

vec4 axonCompassMarker() {
    vec2 p = axonMiniL;
    float dist = axonMiniA.x;
    float side = axonMiniA.y;
    int type = int(fract(axonMiniA.z) * 16.0 + 0.5) & 7;
    float ih = axonMiniB.x;
    float gp = axonMiniB.y;
    float half_ = axonMiniB.z;
    vec4 o = vec4(0.0);
    if (abs(side) < 0.5 && (axonMiniB.w < 0.5 || axonMiniB.w > 1.5)) {
        // odległość pod paskiem (serwer zostawia napis tylko najbliższemu z celów leżących obok siebie),
        // przy środku paska rząd niżej, pod okienkiem stopni
        float y0 = half_ + 2.0 * gp + (axonMiniB.w > 1.5 ? 12.0 * gp : 0.0);
        int n = dist < 9.5 ? 2 : dist < 99.5 ? 3 : dist < 9950.0 ? 4 : 3;
        float w = float(n) * 6.0 * gp + 4.0 * gp;
        float bg = axonRoundBox(p - vec2(0.0, y0 + 5.5 * gp), vec2(w * 0.5, 5.5 * gp), 2.0 * gp);
        o = axonMiniOver(vec4(0.05, 0.06, 0.08, 0.96 * (1.0 - smoothstep(-0.5, 0.5, bg))), o);
        float tc = axonDistanceText(p, 0.0, y0 + 2.0 * gp, gp, dist);
        o = axonMiniOver(vec4(mix(vec3(1.0), AXON_MINI_PINS[type], 0.35), tc), o);
    }
    vec2 l = p / max(ih, 1.0);
    o = axonMiniOver(axonPinAt(l, type, abs(side) > 0.5, vec2(side, 0.0), 1.0 / max(ih, 1.0)), o);
    return o;
}

// ── Okno UI AxonItems (/ustawienia): pudełka i kursor (rendertype_text.vsh, axonUiVertex) ─────────
// Podświetlenie pod kursorem, poświata i kursor są liczone tutaj w każdej klatce, bez serwera.
const vec3 AXON_UI_ACC = vec3(110.0, 220.0, 190.0) / 255.0;

vec4 axonUiOver(vec4 top, vec4 under) {
    float a = top.a + under.a * (1.0 - top.a);
    return vec4((top.rgb * top.a + under.rgb * under.a * (1.0 - top.a)) / max(a, 1e-4), a);
}

// Trójkąt ze znakiem odległości (ujemna w środku).
float axonUiTri(vec2 p, vec2 a, vec2 b, vec2 c) {
    vec2 e0 = b - a, e1 = c - b, e2 = a - c;
    vec2 v0 = p - a, v1 = p - b, v2 = p - c;
    vec2 pq0 = v0 - e0 * clamp(dot(v0, e0) / dot(e0, e0), 0.0, 1.0);
    vec2 pq1 = v1 - e1 * clamp(dot(v1, e1) / dot(e1, e1), 0.0, 1.0);
    vec2 pq2 = v2 - e2 * clamp(dot(v2, e2) / dot(e2, e2), 0.0, 1.0);
    float s = sign(e0.x * e2.y - e0.y * e2.x);
    vec2 d = min(min(vec2(dot(pq0, pq0), s * (v0.x * e0.y - v0.y * e0.x)),
                     vec2(dot(pq1, pq1), s * (v1.x * e1.y - v1.y * e1.x))),
                     vec2(dot(pq2, pq2), s * (v2.x * e2.y - v2.y * e2.x)));
    return -sqrt(d.x) * sign(d.y);
}

float axonUiRing(vec2 p, vec2 c, float r, float w) {
    return abs(length(p - c) - r) - w * 0.5;
}

// Ikony (style 12–31) w polu 16 × 16 jako odległość ze znakiem; wypełnienie tam, gdzie d < 0.
float axonUiIcon(int style, vec2 p) {
    vec2 c = vec2(8.0);
    vec2 q = p - c;
    float d = 1e3;
    if (style == 12) {
        // kompas: pierścień i igła
        d = axonUiRing(p, c, 6.2, 1.3);
        vec2 r = vec2(q.x * 0.7071 + q.y * 0.7071, -q.x * 0.7071 + q.y * 0.7071);
        d = min(d, abs(r.x) * 2.6 + abs(r.y) - 4.2);
    } else if (style == 13) {
        // lista: trzy linie z kropkami
        for (int i = 0; i < 3; i++) {
            float y = 3.5 + float(i) * 4.5;
            d = min(d, length(p - vec2(3.0, y)) - 1.3);
            d = min(d, axonSegment(p, vec2(6.0, y), vec2(13.5, y)) - 0.85);
        }
    } else if (style == 14) {
        // celownik
        d = axonUiRing(p, c, 4.6, 1.3);
        d = min(d, axonSegment(p, vec2(8.0, 0.8), vec2(8.0, 4.0)) - 0.7);
        d = min(d, axonSegment(p, vec2(8.0, 12.0), vec2(8.0, 15.2)) - 0.7);
        d = min(d, axonSegment(p, vec2(0.8, 8.0), vec2(4.0, 8.0)) - 0.7);
        d = min(d, axonSegment(p, vec2(12.0, 8.0), vec2(15.2, 8.0)) - 0.7);
        d = min(d, length(q) - 1.2);
    } else if (style == 15) {
        // dymek
        float shape = min(axonRect(p, 1.0, 2.0, 14.0, 9.5, 3.0), axonUiTri(p, vec2(4.0, 10.5), vec2(4.0, 14.5), vec2(8.0, 10.5)));
        d = abs(shape) - 0.7;
        for (int i = 0; i < 3; i++) d = min(d, length(p - vec2(4.8 + float(i) * 3.2, 6.8)) - 0.95);
    } else if (style == 16) {
        // paleta z dziurką na kciuk i farbami
        d = max(length(q) - 6.8, -(length(p - vec2(10.6, 10.6)) - 1.9));
        d = max(d, -(length(p - vec2(5.0, 6.0)) - 1.3));
        d = max(d, -(length(p - vec2(8.6, 4.2)) - 1.3));
        d = max(d, -(length(p - vec2(4.6, 10.0)) - 1.3));
    } else if (style == 17) {
        // zębatka
        float teeth = smoothstep(-0.25, 0.25, cos(atan(q.y, q.x) * 8.0));
        d = max(length(q) - (5.2 + 1.6 * teeth), -(length(q) - 2.3));
    } else if (style == 18) {
        // gwiazdka
        float k = 6.2831853 / 5.0;
        float a2 = mod(atan(q.x, -q.y) + k * 0.5, k) - k * 0.5;
        vec2 r = length(q) * vec2(cos(a2), abs(sin(a2)));
        d = min(axonUiTri(r, vec2(0.0), vec2(7.2, 0.0), vec2(2.8 * cos(k * 0.5), 2.8 * sin(k * 0.5))), length(q) - 2.7);
    } else if (style == 19) {
        // strzałka dalej
        d = min(axonSegment(p, vec2(5.5, 3.5), vec2(10.5, 8.0)), axonSegment(p, vec2(10.5, 8.0), vec2(5.5, 12.5))) - 1.1;
    } else if (style == 20) {
        // lupa
        d = min(axonUiRing(p, vec2(6.8, 6.8), 4.3, 1.5), axonSegment(p, vec2(10.0, 10.0), vec2(14.0, 14.0)) - 1.2);
    } else if (style == 21) {
        // serce
        vec2 h = vec2(abs(q.x), -q.y + 1.5);
        d = min(length(h - vec2(2.9, 2.2)) - 3.3, axonUiTri(vec2(abs(q.x), q.y), vec2(0.0, 6.6), vec2(6.1, 0.2), vec2(0.0, -1.0)));
    } else if (style == 22) {
        // dom
        d = min(axonUiTri(p, vec2(8.0, 1.5), vec2(15.0, 8.0), vec2(1.0, 8.0)), axonRect(p, 3.0, 7.0, 10.0, 7.5, 0.8));
        d = max(d, -axonRect(p, 6.5, 9.5, 3.0, 5.0, 0.5));
    } else if (style == 23) {
        // rdzeń: diament z połyskiem
        d = abs(q.x) * 0.95 + abs(q.y + 0.5) * 0.75 - 5.2;
        d = max(d, -(abs(q.x) * 0.95 + abs(q.y + 0.5) * 0.75 - 2.4));
        d = min(d, abs(q.x) * 0.95 + abs(q.y + 0.5) * 0.75 - 1.0);
    } else if (style == 24) {
        // nagrobek z krzyżem
        d = axonRect(p, 3.0, 2.0, 10.0, 12.5, 4.5);
        d = max(d, -min(axonRect(p, 7.2, 4.5, 1.6, 7.0, 0.3), axonRect(p, 5.2, 6.4, 5.6, 1.6, 0.3)));
    } else if (style == 25) {
        // ramka: rogi
        float a = min(axonSegment(p, vec2(2.0, 2.0), vec2(6.0, 2.0)), axonSegment(p, vec2(2.0, 2.0), vec2(2.0, 6.0)));
        a = min(a, min(axonSegment(p, vec2(14.0, 14.0), vec2(10.0, 14.0)), axonSegment(p, vec2(14.0, 14.0), vec2(14.0, 10.0))));
        a = min(a, min(axonSegment(p, vec2(14.0, 2.0), vec2(10.0, 2.0)), axonSegment(p, vec2(14.0, 2.0), vec2(14.0, 6.0))));
        a = min(a, min(axonSegment(p, vec2(2.0, 14.0), vec2(6.0, 14.0)), axonSegment(p, vec2(2.0, 14.0), vec2(2.0, 10.0))));
        d = min(a - 1.0, axonRect(p, 5.5, 5.5, 5.0, 5.0, 1.0));
    } else if (style == 26) {
        // zegar
        d = axonUiRing(p, c, 6.2, 1.3);
        d = min(d, axonSegment(p, c, vec2(8.0, 4.0)) - 0.8);
        d = min(d, axonSegment(p, c, vec2(11.0, 9.5)) - 0.8);
    } else if (style == 27) {
        // start
        d = axonUiTri(p, vec2(4.5, 2.5), vec2(4.5, 13.5), vec2(13.5, 8.0)) - 0.6;
    } else if (style == 28) {
        // tarcza
        d = min(axonRect(p, 2.5, 1.5, 11.0, 8.5, 2.0), axonUiTri(p, vec2(2.5, 8.0), vec2(13.5, 8.0), vec2(8.0, 15.0)));
    } else if (style == 29) {
        // oko
        float lens = max(length(p - vec2(8.0, 14.5)) - 10.0, length(p - vec2(8.0, 1.5)) - 10.0);
        d = max(lens, -(length(q) - 3.6));
        d = min(d, length(q) - 1.9);
    } else if (style == 30) {
        // informacja
        d = max(length(q) - 7.0, -min(length(p - vec2(8.0, 4.6)) - 1.3, axonRect(p, 7.0, 6.8, 2.0, 5.8, 0.8)));
    } else {
        // flaga
        d = min(axonSegment(p, vec2(3.5, 1.5), vec2(3.5, 15.0)) - 0.9, axonUiTri(p, vec2(4.0, 2.0), vec2(14.0, 5.5), vec2(4.0, 9.0)));
    }
    return d;
}

// Kolor plakietki ikony (stan 2–3: kolorowy kwadrat z białym znakiem).
vec3 axonUiIconColor(int style) {
    if (style == 12) return vec3(0.33, 0.78, 0.47);
    if (style == 13) return vec3(0.35, 0.58, 1.0);
    if (style == 14) return vec3(1.0, 0.55, 0.24);
    if (style == 15) return vec3(0.66, 0.47, 1.0);
    if (style == 16) return vec3(1.0, 0.43, 0.67);
    if (style == 18) return vec3(1.0, 0.78, 0.25);
    if (style == 19) return vec3(0.45, 0.5, 0.58);
    if (style == 20) return vec3(0.3, 0.78, 0.9);
    if (style == 21) return vec3(1.0, 0.38, 0.45);
    if (style == 22) return vec3(0.95, 0.62, 0.3);
    if (style == 23) return vec3(0.35, 0.9, 0.85);
    if (style == 24) return vec3(0.58, 0.6, 0.66);
    if (style == 25) return vec3(0.3, 0.75, 0.68);
    if (style == 26) return vec3(1.0, 0.72, 0.28);
    if (style == 27) return vec3(0.4, 0.85, 0.4);
    if (style == 28) return vec3(0.4, 0.55, 0.95);
    if (style == 29) return vec3(0.72, 0.5, 0.95);
    if (style == 30) return vec3(0.35, 0.62, 1.0);
    if (style == 31) return vec3(0.95, 0.35, 0.35);
    return AXON_UI_ACC;
}

vec4 axonUiBox() {
    vec2 size = axonHudBox.xy;
    int style = int(axonHudBox.z + 0.5);
    int state = int(axonHudBox.w + 0.5);
    vec2 p = axonHudLocal;
    float r = axonHudExtra.z;
    vec2 cur = axonCursor * vec2(640.0, 384.0) - axonHudExtra.xy;
    float aa = max(fwidth(p.x), 1e-3);
    float t = GameTime * 24000.0 / 20.0;
    bool lit = state == 1 || state == 3;

    if (style == 0) {
        // szyba: jak przezroczyste piksele mapy, ale w tym samym napisie co pudełka,
        // więc jest też pod ich cieniami i półprzezroczystymi brzegami
        vec2 e = (axonHudExtra.xy + p) / vec2(640.0, 384.0) - 0.5;
        float vig = smoothstep(0.2, 0.75, length(e * vec2(1.15, 1.0)));
        return vec4(0.015, 0.02, 0.03, 0.5 + 0.25 * vig);
    }

    if (style >= 12) {
        float v0 = clamp(p.y / size.y, 0.0, 1.0);
        float gd = axonUiIcon(style, p - (size - 16.0) * 0.5);
        float glyph = 1.0 - smoothstep(-aa * 0.75, aa * 0.75, gd);
        if (state >= 2) {
            // plakietka: kolorowy zaokrąglony kwadrat z białym znakiem; stan 3 = świeci (aktywna karta)
            vec3 bc = axonUiIconColor(style);
            float bd = axonRoundBox(p - size * 0.5, size * 0.5, 6.0);
            float bin = 1.0 - smoothstep(-aa, aa, bd);
            vec3 bcol = mix(bc * 1.12, bc * 0.78, v0);
            bcol = mix(bcol, bcol + vec3(0.25), (1.0 - smoothstep(0.0, 1.2, -bd)) * (1.0 - v0));
            vec4 o = vec4(mix(bcol, vec3(1.0), glyph * 0.95), bin);
            vec4 under = state == 3
                    ? vec4(bc, (0.35 + 0.1 * sin(t * 2.5)) * (1.0 - smoothstep(0.0, 7.0, bd)))
                    : vec4(0.0, 0.0, 0.0, 0.3 * (1.0 - smoothstep(-1.0, 4.0, bd - 1.0)));
            return axonUiOver(o, under);
        }
        vec3 ic = state == 1 ? AXON_UI_ACC : vec3(0.82, 0.85, 0.9);
        return vec4(ic, glyph);
    }

    float d = axonRoundBox(p - size * 0.5, size * 0.5, r);
    float inside = 1.0 - smoothstep(-aa, aa, d);

    if (style == 11) {
        // przełącznik: tor i gałka; włączony = akcent, gałka po prawej
        float on = lit ? 1.0 : 0.0;
        vec3 track = mix(vec3(0.22, 0.24, 0.29), AXON_UI_ACC * 0.85, on);
        vec4 o = vec4(track, inside * 0.95);
        o.rgb = mix(o.rgb, o.rgb + vec3(0.12), 1.0 - smoothstep(0.0, 1.2, -d));
        vec2 kc = vec2(mix(8.0, size.x - 8.0, on), size.y * 0.5);
        float kd = length(p - kc) - 5.6;
        vec4 shadow = vec4(0.0, 0.0, 0.0, 0.35 * (1.0 - smoothstep(-1.0, 2.0, length(p - kc - vec2(0.0, 1.0)) - 5.6)));
        vec4 knob = vec4(vec3(0.97), 1.0 - smoothstep(-aa, aa, kd));
        vec4 under = vec4(0.0, 0.0, 0.0, 0.25 * (1.0 - smoothstep(-1.0, 4.0, d)));
        return axonUiOver(knob, axonUiOver(shadow, axonUiOver(o, under)));
    }

    if (style == 9) {
        float f = 1.0 - clamp(p.x / max(size.x, 1.0), 0.0, 1.0);
        float m = 1.0 - smoothstep(0.0, 1.0, abs(p.y - 0.5) - 0.2);
        return vec4(mix(vec3(0.5), AXON_UI_ACC, f), 0.45 * f * m * step(0.0, p.x) * step(p.x, size.x));
    }

    bool button = style == 3 || style == 4 || style == 5 || style == 7;
    bool hot = button && state != 2 && cur.x >= 0.0 && cur.y >= 0.0 && cur.x < size.x && cur.y < size.y;
    float v = clamp(p.y / size.y, 0.0, 1.0);

    if (style == 1) {
        // szyna: ciemne szkło przy lewej krawędzi, jasna linia po prawej, poświata akcentu pod tytułem
        if (p.x < 0.0 || p.y < 0.0 || p.y > size.y) return vec4(0.0);
        if (p.x > size.x) {
            // miękki cień szyny na świecie
            return vec4(0.0, 0.0, 0.0, 0.35 * (1.0 - smoothstep(0.0, 10.0, p.x - size.x)));
        }
        vec3 col = mix(vec3(0.05, 0.055, 0.07), vec3(0.03, 0.033, 0.042), v);
        col += AXON_UI_ACC * 0.09 * (1.0 - smoothstep(0.0, 160.0, length(p - vec2(20.0, 20.0))));
        float edge = 1.0 - smoothstep(0.0, 1.0, size.x - p.x);
        col = mix(col, vec3(0.3, 0.33, 0.38), edge * 0.8);
        // linia pod tytułem z błyskiem
        float line = (1.0 - smoothstep(0.3, 1.0, abs(p.y - 40.5))) * step(12.0, p.x) * step(p.x, size.x - 12.0);
        float shine = pow(0.5 + 0.5 * sin(t * 1.1 - p.x * 0.03), 8.0);
        col = mix(col, mix(vec3(0.25), AXON_UI_ACC, 0.5 + 0.5 * shine), line * 0.8);
        return vec4(col, 0.9);
    }

    vec4 under = vec4(0.0);
    vec3 col = vec3(0.0);
    float alpha = 0.0;

    if (style == 2) {
        // karta szczegółów: szkło z jasną górną krawędzią
        float ds = axonRoundBox(p - size * 0.5 - vec2(0.0, 3.0), size * 0.5, r + 2.0);
        under = vec4(0.0, 0.0, 0.0, 0.4 * (1.0 - smoothstep(-3.0, 9.0, ds)));
        col = mix(vec3(0.075, 0.082, 0.1), vec3(0.045, 0.05, 0.062), v);
        col += AXON_UI_ACC * 0.06 * (1.0 - smoothstep(0.0, 120.0, length(p - vec2(26.0, 24.0))));
        alpha = 0.86;
        float rim = 1.0 - smoothstep(0.0, 1.2, -d);
        col = mix(col, vec3(1.0), rim * mix(0.22, 0.05, v));
        alpha = max(alpha, rim * mix(0.22, 0.05, v));
    } else if (style == 3) {
        // karta pluginu: aktywna ma gradient akcentu od lewej i pasek; najechana jasne tło
        if (lit) {
            float g = 1.0 - clamp(p.x / size.x, 0.0, 1.0);
            col = mix(vec3(0.08, 0.09, 0.1), AXON_UI_ACC, 0.18 + 0.12 * g);
            alpha = 0.3 + 0.55 * g;
        }
        if (hot) {
            col = lit ? col + vec3(0.04) : vec3(0.2, 0.21, 0.24);
            alpha = max(alpha, 0.55);
        }
        if (lit) {
            float pulse = 0.85 + 0.15 * sin(t * 2.2);
            float bar = axonRect(p, 0.0, 5.0, 2.5, size.y - 10.0, 1.25);
            float m = 1.0 - smoothstep(-aa, aa, bar);
            col = mix(col, AXON_UI_ACC * pulse + vec3(0.06), m);
            alpha = max(alpha, m);
        }
    } else if (style == 4) {
        // zakładka: tekst nad podkreśleniem; aktywna ma pełne podkreślenie akcentu
        if (hot) {
            col = vec3(0.2, 0.21, 0.24);
            alpha = 0.45;
        }
        float ul = axonRect(p, 6.0, size.y - 2.0, size.x - 12.0, 2.0, 1.0);
        float m = (1.0 - smoothstep(-aa, aa, ul)) * (lit ? 1.0 : (hot ? 0.45 : 0.0));
        col = mix(col, lit ? AXON_UI_ACC : vec3(0.6), m);
        alpha = max(alpha, m);
        if (lit) {
            under = vec4(AXON_UI_ACC, 0.25 * (1.0 - smoothstep(0.0, 5.0, ul)));
        }
    } else if (style == 5) {
        // wiersz: przezroczysty z cienką linią pod spodem; najechany ma jasne tło, pasek i światło pod kursorem
        float sep = (1.0 - smoothstep(0.2, 0.9, abs(p.y - (size.y - 0.5)))) * step(30.0, p.x) * step(p.x, size.x - 4.0);
        col = vec3(1.0);
        alpha = 0.06 * sep;
        if (hot) {
            col = vec3(0.22, 0.24, 0.27) + AXON_UI_ACC * 0.12 * (1.0 - smoothstep(0.0, 90.0, length(p - cur)));
            alpha = 0.55 * inside;
            float bar = axonRect(p, 0.0, 5.0, 2.0, size.y - 10.0, 1.0);
            float m = 1.0 - smoothstep(-aa, aa, bar);
            col = mix(col, AXON_UI_ACC, m);
            alpha = max(alpha, m);
            float rim = (1.0 - smoothstep(0.0, 1.0, -d)) * inside;
            col = mix(col, AXON_UI_ACC, rim * 0.35);
            alpha = max(alpha, rim * 0.35);
        }
        if (state == 2) alpha *= 0.5;
        return vec4(col, alpha);
    } else if (style == 6) {
        // klawisz: nakładka z grubszym dołem
        float body = axonRoundBox(p - vec2(size.x * 0.5, size.y * 0.5 - 0.75), vec2(size.x * 0.5, size.y * 0.5 - 0.75), r);
        float base = d;
        col = mix(vec3(0.07, 0.075, 0.09), vec3(0.24, 0.25, 0.29), 1.0 - smoothstep(-aa, aa, body));
        col = mix(col, vec3(0.32, 0.34, 0.38), (1.0 - smoothstep(0.0, 1.0, -body)) * (1.0 - v) * 0.8);
        alpha = 0.95;
        inside = 1.0 - smoothstep(-aa, aa, base);
    } else if (style == 7) {
        col = vec3(0.14, 0.15, 0.18);
        alpha = hot ? 0.9 : 0.55;
        if (hot) col = vec3(0.32, 0.12, 0.12);
        vec2 c = size * 0.5;
        float x = min(axonSegment(p, c - vec2(4.0), c + vec2(4.0)), axonSegment(p, c + vec2(-4.0, 4.0), c + vec2(4.0, -4.0)));
        float m = 1.0 - smoothstep(0.85 - aa, 0.85 + aa, x);
        col = mix(col, hot ? vec3(1.0, 0.6, 0.58) : vec3(0.82, 0.84, 0.88), m);
        alpha = max(alpha, m);
        float rim = 1.0 - smoothstep(0.0, 1.2, -d);
        col = mix(col, vec3(1.0), rim * 0.12);
    } else if (style == 10) {
        col = state == 2 ? vec3(0.35, 0.1, 0.1) : mix(vec3(0.07, 0.09, 0.1), AXON_UI_ACC, 0.16);
        alpha = 0.88;
        float rim = 1.0 - smoothstep(0.0, 1.2, -d);
        col = mix(col, state == 2 ? vec3(1.0, 0.45, 0.4) : AXON_UI_ACC, rim * 0.45);
    }
    return axonUiOver(vec4(col, alpha * inside), under);
}

// Kursor: strzałka z czarną obwódką i miękkim cieniem; czubek w punkcie kursora (lokalnie 3, 3).
vec4 axonUiCursor() {
    vec2 p = axonHudLocal - vec2(3.0);
    float aa = max(fwidth(p.x), 1e-3);
    vec2 a = vec2(0.0), b = vec2(0.0, 13.0), c = vec2(9.5, 9.5);
    float d = axonUiTri(p, a, b, c);
    float tail = axonSegment(p, vec2(3.5, 8.0), vec2(6.5, 14.0)) - 1.6;
    d = min(d, tail);
    float ds = min(axonUiTri(p - vec2(1.0, 1.5), a, b, c), axonSegment(p - vec2(1.0, 1.5), vec2(3.5, 8.0), vec2(6.5, 14.0)) - 1.6);
    vec4 shadow = vec4(0.0, 0.0, 0.0, 0.35 * (1.0 - smoothstep(-1.0, 2.5, ds)));
    float fill = 1.0 - smoothstep(-aa, aa, d + 1.0);
    float edge = 1.0 - smoothstep(-aa, aa, d);
    vec4 arrow = vec4(mix(vec3(0.05), vec3(1.0), fill), edge);
    return axonUiOver(arrow, shadow);
}

void main() {
    if (axonHud >= 20) {
        fragColor = axonHud == 21 ? axonUiCursor() : axonUiBox();
        if (fragColor.a < 0.004) {
            discard;
        }
        return;
    }
    if (axonMiniA.z > 0.5) {
        int k = int(axonMiniA.z);
        if (k == 5) {
            fragColor = axonMiniTile();
        } else if (k == 3) {
            fragColor = axonMiniPin();
        } else if (k == 6) {
            fragColor = axonCompassBar();
        } else if (k == 7) {
            fragColor = axonCompassMarker();
        } else {
            fragColor = axonMiniFrame(k == 2);
        }
        if (fragColor.a < 0.004) {
            discard;
        }
        return;
    }
    if (axonHud == 4) {
        fragColor = axonHudBar();
        if (fragColor.a < 0.004) {
            discard;
        }
        return;
    }
    if (axonHud == 5) {
        fragColor = axonHudToast();
        if (fragColor.a < 0.004) {
            discard;
        }
        return;
    }
    if (axonHud == 8) {
        fragColor = axonHudTimer();
        return;
    }
    if (axonHud == 7) {
        fragColor = axonHudBanner();
        if (fragColor.a < 0.004) {
            discard;
        }
        return;
    }
    if (axonHud == 2) {
        fragColor = axonHudBackground();
        if (fragColor.a < 0.004) {
            discard;
        }
        return;
    }
    if (axonHud == 3) {
        float f = 1.0 - clamp(axonHudLocal.x / max(axonHudBox.x, 1.0), 0.0, 1.0);
        fragColor = vec4(axonHudAccent(axonHudLocal.x), 0.25 + 0.6 * f);
        return;
    }
    if (axonMap == 1) {
        // Mapa AxonMap: bez światła i mgły.
        // Obie gęstości skalujemy gładko: 384 wiersze mapy na 1080 px ekranu to 2,81 px na piksel,
        // a bez tego część wierszy ma 2 px, część 3 px i litery wychodzą nierówne.
        fragColor = vec4(axonSharp(texCoord0), 1.0);

        // Sprity i kursor są w pikselach logicznych ekranu 640x384, niezależnie od gęstości siatki.
        int cols = AXON_COLS * axonDensity;
        float density = float(axonDensity);
        vec2 mapPixel = (vec2(float(axonTile % cols), float(axonTile / cols)) * 128.0 + texCoord0 * 128.0) / density;
        vec2 cursorPixel = axonCursor * vec2(float(AXON_COLS), float(AXON_ROWS)) * 128.0;
        // Przezroczyste piksele mapy (kolor 0, okno /ustawienia): za przyciemnioną szybą widać świat.
        // Wiersze 0 i 127 niosą znaczniki kafla, więc dla nich sprawdzamy sąsiedni wiersz.
        ivec2 axonTp = ivec2(clamp(floor(texCoord0 * 128.0), 0.0, 127.0));
        axonTp.y = axonTp.y == 0 ? 1 : (axonTp.y == 127 ? 126 : axonTp.y);
        if (texelFetch(Sampler0, axonTp, 0).a < 0.5) {
            vec2 e = mapPixel / vec2(640.0, 384.0) - 0.5;
            float vig = smoothstep(0.2, 0.75, length(e * vec2(1.15, 1.0)));
            fragColor = vec4(0.015, 0.02, 0.03, 0.5 + 0.25 * vig);
            return;
        }

        // Sprity: rysowane w pikselach logicznych, z wygładzaniem do rozdzielczości ekranu.
        float spriteAa = max(fwidth(mapPixel.x), 1e-3);
        vec3 spriteBase = fragColor.rgb;
        for (int i = 0; i < AXON_SPRITES; i++) {
            axonSprite(spriteBase, mapPixel, spriteAa, cursorPixel, i);
        }
        fragColor = vec4(spriteBase, 1.0);

        // Kursor: krzyżyk z obwódką.
        vec2 d = abs(floor(mapPixel) - floor(cursorPixel));
        if ((d.x <= 5.0 && d.y <= 0.0) || (d.y <= 5.0 && d.x <= 0.0)) {
            fragColor = vec4(1.0);
        } else if ((d.x <= 6.0 && d.y <= 1.0) || (d.y <= 6.0 && d.x <= 1.0)) {
            fragColor = vec4(0.0, 0.0, 0.0, 1.0);
        }
        return;
    }

    vec4 color = texture(Sampler0, texCoord0) * vertexColor * ColorModulator;
    if (color.a < 0.1) {
        discard;
    }
    fragColor = apply_fog(color, sphericalVertexDistance, cylindricalVertexDistance, FogEnvironmentalStart, FogEnvironmentalEnd, FogRenderDistanceStart, FogRenderDistanceEnd, FogColor);
}
