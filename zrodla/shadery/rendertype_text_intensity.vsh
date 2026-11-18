#version 150

#moj_import <minecraft:fog.glsl>

in vec3 Position;
in vec4 Color;
in vec2 UV0;
in ivec2 UV2;

uniform sampler2D Sampler2;

uniform mat4 ModelViewMat;
uniform mat4 ProjMat;
uniform int FogShape;
uniform float GameTime;

out float vertexDistance;
out vec4 vertexColor;
out vec2 texCoord0;

// Napisy okna UI AxonItems (/ustawienia) w czcionce Inter (axon:ui, TTF). Glify TTF są w teksturze
// jednokanałowej, więc klient rysuje je tym shaderem, a nie rendertype_text. Pozycja jak w axonUiVertex
// z rendertype_text.vsh (alfa 253, odległość w widoku ~AXON_UI_DEPTH, otwarte pełne GUI).
#define AXON_UI_DEPTH 1.0
#define AXON_UI_UNIT 0.25
#define AXON_UI_ANIM 100.0   // jak w rendertype_text.vsh; napisy mają warstwę AXON_UI_DEPTH
#define AXON_HUD_TIME 12000.0
#define AXON_HUD_WINDOW 140.0

bool axonUiLabel() {
    float t = GameTime * 24000.0;
    if (ProjMat[2][3] == 0.0 || t < AXON_HUD_TIME || t >= AXON_HUD_TIME + AXON_HUD_WINDOW) {
        return false;
    }
    if (abs(floor(Color.a * 255.0 + 0.5) - 253.0) > 0.5) {
        return false;
    }
    // Encje okna mają billboard FIXED i yaw 180 (UiDisplays), więc ich układ to stały układ świata:
    // lokalne x = -świat x, lokalne z = -świat z. Position to położenie względem kamery w świecie, więc
    // nie zależy od obrotu kamery (billboard CENTER przechylał napisy przy patrzeniu góra-dół).
    vec4 view = vec4(-Position.x, Position.y, -Position.z, 1.0);
    float az = abs(view.z);
    if (az > AXON_UI_DEPTH + AXON_UI_ANIM + 20.0) {
        return false;
    }
    float show = 1.0 - clamp((az - AXON_UI_DEPTH) / AXON_UI_ANIM, 0.0, 1.0);
    show = show * show * (3.0 - 2.0 * show);   // pojawianie się, jak w rendertype_text.vsh
    vec2 px = vec2(320.0 + view.x / AXON_UI_UNIT, 192.0 - view.y / AXON_UI_UNIT + 6.0 * (1.0 - show));
    gl_Position = vec4(px.x / 320.0 - 1.0, 1.0 - px.y / 192.0, -0.9960, 1.0);
    vertexColor = vec4(Color.rgb, show);
    texCoord0 = UV0;
    return true;
}

void main() {
    if (axonUiLabel()) {
        vertexDistance = 0.0;
        return;
    }
    gl_Position = ProjMat * ModelViewMat * vec4(Position, 1.0);

    vertexDistance = fog_distance(Position, FogShape);
    vertexColor = Color * texelFetch(Sampler2, UV2 / 16, 0);
    texCoord0 = UV0;
}
