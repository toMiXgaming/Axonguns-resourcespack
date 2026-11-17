// Zamrożony świat przy otwartym oknie (nakładka AxonItems: /ustawienia, /mapa i inne).
// Plugin ustawia czas gry w oknie [AXON_FREEZE_TIME, +AXON_FREEZE_WINDOW) (OverlayLayout.HUD_TIME)
// i obraca gracza na yaw 0 / pitch 0. Mysz dalej obraca kamerę (z niej shader liczy kursor),
// ale świat rysujemy ze stałego widoku yaw 0 / pitch 0 i stałego pola widzenia, więc stoi w miejscu.
// Plugin poszerza pole widzenia gry na czas okna, żeby gra nie ucinała bloków poza prawdziwym
// polem widzenia kamery (CURSOR_YAW_RANGE / CURSOR_PITCH_RANGE mieszczą się w zapasie).
// Wymaga globals.glsl (GameTime).
#define AXON_FREEZE_TIME 12000.0
#define AXON_FREEZE_WINDOW 60.0
#define AXON_FREEZE_FOV 70.0

bool axonFrozen(mat4 proj) {
    float t = GameTime * 24000.0;
    return proj[2][3] != 0.0 && t >= AXON_FREEZE_TIME && t < AXON_FREEZE_TIME + AXON_FREEZE_WINDOW;
}

// Widok kamery Minecrafta dla yaw 0 / pitch 0 (patrzy na +z świata).
const mat3 AXON_FREEZE_VIEW = mat3(-1.0, 0.0, 0.0,  0.0, 1.0, 0.0,  0.0, 0.0, -1.0);

// ModelViewMat świata to obrót kamery razy ewentualne własne przekształcenie rysowanej rzeczy.
// Zdejmujemy obrót kamery i wstawiamy stały. Rzeczy rysowane bez obrotu kamery (ręka) zostają.
mat4 axonWorldView(mat4 mv, mat4 proj) {
    if (!axonFrozen(proj)) return mv;
    mat3 r = mat3(mv);
    if (abs(r[0][0] - 1.0) + abs(r[1][1] - 1.0) + abs(r[2][2] - 1.0) < 1e-4) return mv;
    return mat4(AXON_FREEZE_VIEW) * mat4(transpose(r)) * mv;
}

// Stałe pole widzenia zamiast poszerzonego przez plugin.
mat4 axonWorldProj(mat4 proj) {
    if (!axonFrozen(proj)) return proj;
    float k = (1.0 / tan(radians(AXON_FREEZE_FOV * 0.5))) / proj[1][1];
    proj[0][0] *= k;
    proj[1][1] *= k;
    return proj;
}
