#version 150

in vec3 Position;
in vec4 Color;

uniform mat4 ModelViewMat;
uniform mat4 ProjMat;
uniform float GameTime;

out vec4 vertexColor;

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

    vertexColor = Color;
    // Przyciemnienie świata za oknem (fillGradient 0xC0101010 → 0xD0101010) znika przy menu broni.
    if (ProjMat[2][3] == 0.0 && axonGunMenuOpen(GameTime)
            && all(lessThan(abs(Color.rgb - vec3(16.0 / 255.0)), vec3(0.5 / 255.0)))
            && Color.a > 0.70 && Color.a < 0.85) {
        vertexColor.a = 0.0;
    }
}
