#version 330

// Nie ma moj_import: ten shader jest używany przy starcie, gdy paczki zasobów jeszcze nie istnieją.
layout(std140) uniform DynamicTransforms {
    mat4 ModelViewMat;
    vec4 ColorModulator;
    vec3 ModelOffset;
    mat4 TextureMat;
};
layout(std140) uniform Projection {
    mat4 ProjMat;
};
layout(std140) uniform Globals {
    ivec3 CameraBlockPos;
    vec3 CameraOffset;
    vec2 ScreenSize;
    float GlintAlpha;
    float GameTime;
    int MenuBlurRadius;
    int UseRgss;
};

uniform sampler2D Sampler0;

in vec3 Position;
in vec2 UV0;
in vec4 Color;

out vec2 texCoord0;
out vec4 vertexColor;
out vec2 axonGui;
flat out int axonHide;
flat out int axonGunMenu;

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

// AxonGuns: przy otwartym menu akcesoriów broni (Shift+F) plugin wysyła czas gry, którego reszta
// z 24000 jest w [AXON_GUN_MENU_TIME, +AXON_GUN_MENU_WINDOW) (MenuLayout.SHADER_TIME). Wtedy tło
// skrzyni (generic_54.png ze znacznikiem w pikselu 255,255) i przyciemnienie świata znikają,
// żeby broń w ręce było widać przez okno.
#define AXON_GUN_MENU_TIME 12200.0
#define AXON_GUN_MENU_WINDOW 60.0

bool axonGunMenuOpen(float gameTime) {
    float t = gameTime * 24000.0;
    return t >= AXON_GUN_MENU_TIME && t < AXON_GUN_MENU_TIME + AXON_GUN_MENU_WINDOW;
}

// Menu broni: podświetlenie slotu (slot_highlight_back/front z paczki) ma w rogach znaczniki o alfie 1.
// Wierzchołek w rogu takiego sprite'a liczy, który slot okna 9×6 podświetla; dla martwych slotów
// (wszystko poza miejscami na akcesoria i przyciskami, MenuLayout) cały kwadrat znika.
bool axonMarker(ivec2 t, ivec2 size, float code) {
    if (t.x < 0 || t.y < 0 || t.x >= size.x || t.y >= size.y) return false;
    vec4 c = texelFetch(Sampler0, t, 0) * 255.0;
    return abs(c.a - 1.0) < 0.5 && abs(c.r - code) < 0.5 && c.g < 0.5 && c.b < 0.5;
}

bool axonActiveSlot(int i) {
    return i == 0 || i == 9 || i == 18 || i == 27 || i == 8 || i == 17 || i == 26 || i == 35
        || i == 45 || (i >= 47 && i <= 51) || i == 53;
}

bool axonDeadHighlight(vec2 uv, vec2 guiPos, vec2 guiSize) {
    ivec2 size = textureSize(Sampler0, 0);
    ivec2 b = ivec2(floor(uv * vec2(size) + 0.5));
    vec2 corner;
    // róg potwierdzony drugim znacznikiem tego samego sprite'a (sąsiedni sprite w atlasie może mieć swoje)
    if (axonMarker(b, size, 11.0) && axonMarker(b + ivec2(23, 0), size, 12.0)) corner = vec2(0.0, 0.0);
    else if (axonMarker(b + ivec2(-1, 0), size, 12.0) && axonMarker(b + ivec2(-24, 0), size, 11.0)) corner = vec2(24.0, 0.0);
    else if (axonMarker(b + ivec2(0, -1), size, 13.0) && axonMarker(b + ivec2(23, -1), size, 14.0)) corner = vec2(0.0, 24.0);
    else if (axonMarker(b + ivec2(-1, -1), size, 14.0) && axonMarker(b + ivec2(-24, -1), size, 13.0)) corner = vec2(24.0, 24.0);
    else return false;
    vec2 item = guiPos - corner + vec2(4.0) - floor((guiSize - vec2(176.0, 222.0)) * 0.5);
    int c = int(floor((item.x - 8.0) / 18.0 + 0.5));
    int r = int(floor((item.y - 18.0) / 18.0 + 0.5));
    if (c < 0 || c > 8 || r < 0 || r > 5) return false;
    return !axonActiveSlot(r * 9 + c);
}

void main() {
    gl_Position = ProjMat * ModelViewMat * vec4(Position, 1.0);

    texCoord0 = UV0;
    vertexColor = Color;
    axonGui = vec2(0.0);
    axonHide = 0;
    axonGunMenu = ProjMat[2][3] == 0.0 && axonGunMenuOpen(GameTime) ? 1 : 0;
    if (axonGunMenu == 1 && axonDeadHighlight(UV0, axonGuiPos(gl_Position, ProjMat), axonGuiSize(ProjMat))) {
        gl_Position = vec4(-10.0, -10.0, -10.0, 1.0);
    }
    // GUI ma rzut ortogonalny (ProjMat[2][3] == 0).
    if (ProjMat[2][3] == 0.0 && axonMapOpen(GameTime)) {
        axonGui = axonGuiPos(gl_Position, ProjMat);
        axonHide = 1;
        // Nakładki na cały ekran (winieta, dynia, śnieg, portal) mają wierzchołki w rogach ekranu.
        // Chowamy je całe: inaczej mapa ciemnieje przy krawędziach, a przy hotbarze zostaje jasny prostokąt.
        vec2 size = axonGuiSize(ProjMat);
        bool cornerX = axonGui.x <= 0.01 || axonGui.x >= size.x - 0.01;
        bool cornerY = axonGui.y <= 0.01 || axonGui.y >= size.y - 0.01;
        if (cornerX && cornerY) {
            gl_Position = vec4(-10.0, -10.0, -10.0, 1.0);
        }
    }
}
