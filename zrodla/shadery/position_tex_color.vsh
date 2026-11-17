#version 150

in vec3 Position;
in vec2 UV0;
in vec4 Color;

uniform mat4 ModelViewMat;
uniform mat4 ProjMat;
uniform float GameTime;

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

void main() {
    gl_Position = ProjMat * ModelViewMat * vec4(Position, 1.0);

    texCoord0 = UV0;
    vertexColor = Color;
    axonGui = vec2(0.0);
    axonHide = 0;
    axonGunMenu = ProjMat[2][3] == 0.0 && axonGunMenuOpen(GameTime) ? 1 : 0;
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
