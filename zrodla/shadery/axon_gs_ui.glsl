// Menu akcesoriów AxonGuns, część z napisów (rendertype_text.vsh): kafelki miejsc, lista akcesoriów
// i paski statystyk. Encje okna jak w axonUiVertex (UiDisplays), ale alfa tekstu 251.
// Jeden znak = jeden element, kolor znaku go opisuje:
//   R = x / 2 (młodsze 8 bitów), G = y / 2, B = rodzaj 3 bity | stan 2 bity << 3 | p 2 bity << 5 | najstarszy bit x / 2 << 7
//   rodzaj 0 kafelek 64 × 34: stan 0 zwykły, 1 wybrany, 2 wolny; p = kolor grupy miejsca
//   rodzaj 1 tło listy 132 × (wiersze × 22 + 8): wiersze = (stan | p << 2) + 1
//   rodzaj 2 wiersz listy 124 × 20: stan 0 do założenia, 1 założony, 2 brak w ekwipunku, 3 zdejmij
//   rodzaj 3 pasek statystyki: R = wartość bez zmiany (0..255), G = wartość po zmianie, wiersz = stan | p << 2
// Postęp wjazdu (i wzrostu zmiany na pasku) to odsunięcie encji od warstwy, jak w axonUiVertex.
// Stałe muszą zgadzać się z pl.axonitems.gunsmith.GunsmithLayout.
#define AXON_GS_TILE vec2(78.0, 34.0)
#define AXON_GS_DROP_W 132.0
#define AXON_GS_ROW_H 22.0
#define AXON_GS_OPT vec2(124.0, 20.0)
#define AXON_GS_BAR_X 26.0
#define AXON_GS_BAR_Y0 106.0
#define AXON_GS_BAR_STEP 30.0
#define AXON_GS_BAR vec2(144.0, 4.0)

bool axonGsUiVertex() {
    if (ProjMat[2][3] == 0.0 || !axonMapOpen(GameTime)) {
        return false;
    }
    float a = floor(Color.a * 255.0 + 0.5);
    if (abs(a - 251.0) > 0.5) {
        return false;
    }
    vec4 view = vec4(-Position.x, Position.y, -Position.z, 1.0);
    float az = abs(view.z);
    if (az > AXON_UI_FAR) {
        return false;
    }
    float lvl = axonUiLayer(az);
    float show = 1.0 - clamp((az - lvl) / AXON_UI_ANIM, 0.0, 1.0);
    show = show * show * (3.0 - 2.0 * show);
    ivec3 c = ivec3(floor(Color.rgb * 255.0 + 0.5));
    int kind = c.b & 7;
    int state = (c.b >> 3) & 3;
    int pp = (c.b >> 5) & 3;
    vec2 org;
    vec2 size;
    float z;
    float pad;
    if (kind == 3) {
        int row = state | (pp << 2);
        org = vec2(AXON_GS_BAR_X, AXON_GS_BAR_Y0 + float(row) * AXON_GS_BAR_STEP);
        size = AXON_GS_BAR;
        z = -0.99250;
        pad = 2.0;
        axonHudAcc2 = vec4(float(c.r) / 255.0, float(c.g) / 255.0, show, 0.0);
        state = 0;
    } else {
        org = vec2(float(c.r | ((c.b >> 7) << 8)), float(c.g)) * 2.0;
        if (kind == 0) {
            size = AXON_GS_TILE;
            z = -0.99280;
            pad = 8.0;
        } else if (kind == 1) {
            size = vec2(AXON_GS_DROP_W, float((state | (pp << 2)) + 1) * AXON_GS_ROW_H + 8.0);
            z = -0.99400;
            pad = 10.0;
        } else {
            size = AXON_GS_OPT;
            z = -0.99420;
            pad = 2.0;
        }
        org.y += 6.0 * (1.0 - show);
    }
    vec3 forward = -vec3(ModelViewMat[0][2], ModelViewMat[1][2], ModelViewMat[2][2]);
    float yaw = degrees(atan(-forward.x, forward.z));
    float pitch = degrees(asin(clamp(-forward.y, -1.0, 1.0)));
    axonCursor = clamp(vec2(0.5 + yaw / AXON_YAW_RANGE, 0.5 + pitch / AXON_PITCH_RANGE), 0.0, 1.0);
    int vc = gl_VertexID % 4;
    vec2 cv = vec2(vc == 2 || vc == 3 ? 1.0 : 0.0, vc == 1 || vc == 2 ? 1.0 : 0.0);
    vec2 local = mix(vec2(-pad), size + pad, cv);
    gl_Position = axonUiClip(org + local, z);
    axonHud = 22;
    axonHudLocal = local;
    axonHudBox = vec4(size, float(kind), float(state));
    axonHudExtra = vec4(org, float(pp), show);
    vertexColor = vec4(1.0);
    texCoord0 = UV0;
    return true;
}
