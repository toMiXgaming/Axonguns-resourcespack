// Broń, ikony akcesoriów i linie menu AxonGuns (opis w axon_gs.glsl). Ustawia gl_Position, vertexColor
// i dane linii (axonGsA, axonGsB, axonGsP) dla fragmentu.
// Światło własne, jak w studiu: główne z lewej z góry, wypełniające z prawej i chłodna krawędź od tyłu.
bool axonGsItem(mat4 proj) {
    axonGsA = vec4(0.0);
    axonGsB = vec4(0.0);
    axonGsP = vec2(0.0);
    if (proj[2][3] == 0.0 || !axonGsTime()) return false;
    // First-person items use an unrotated view near the camera.
    // Run this after initializing the fragment shader varyings.
    mat3 view = mat3(ModelViewMat);
    float rotationDelta = length(view[0] - vec3(1.0, 0.0, 0.0))
                        + length(view[1] - vec3(0.0, 1.0, 0.0))
                        + length(view[2] - vec3(0.0, 0.0, 1.0));
    if (rotationDelta < 0.0001 && dot(Position, Position) < 9.0) return false;
    if (UV2 == AXON_GS_LINK_LIGHT) {
        ivec3 c = ivec3(floor(Color.rgb * 255.0 + 0.5));
        vec2 b = vec2(float(c.r | ((c.b >> 7) << 8)), float(c.g)) * 2.0;
        b = axonGsSway(b, 0.0).xy;
        vec2 a = vec2((abs(Position.y) * 2.0 - 1.0) * 8.0, (-Position.z - 10.0) * 8.0);
        float prog = clamp((abs(Position.x) * 2.0 - 1.0) / 9.0, 0.0, 1.0);
        vec2 e = b - a;
        float len = max(length(e), 1e-3);
        vec2 dir = e / len;
        vec2 perp = vec2(dir.y, -dir.x);
        float cu = Position.x > 0.0 ? 1.0 : 0.0;
        float cv = Position.y > 0.0 ? 1.0 : 0.0;
        float m = AXON_GS_LINK_PAD;
        vec2 p = a - dir * m + dir * (len + 2.0 * m) * cu + perp * (cv - 0.5) * 2.0 * m;
        gl_Position = axonGsClip(p, -0.99200);
        axonGsA = vec4(1.0, float(c.b & 3), b);
        axonGsB = vec4(a, prog, 0.0);
        axonGsP = p;
        vertexColor = vec4(1.0);
        return true;
    }
    bool gun = UV2 == AXON_GS_GUN_LIGHT;
    if (!gun && UV2 != AXON_GS_ICON_LIGHT) return false;
    vec3 p = Position / AXON_GS_UNIT;
    vec2 canvas = vec2(320.0 + p.x, 192.0 - p.y);
    vec3 n = normalize(Normal);
    float z;
    if (gun) {
        vec3 s = axonGsSway(canvas, p.z);
        canvas = s.xy;
        n = axonGsSwayRot() * n;
        // przed szybą i kartą statystyk, za liniami i kafelkami (pudełka okna mają -0,9900 … -0,9930)
        z = -0.99150 - clamp(s.z, -60.0, 60.0) * 0.000005;
    } else {
        // ikona: encja kafelka ma z = -10 bloków (nad kafelkiem), encja listy z = -20 (nad listą);
        // odstęp większy niż grubość modelu (do ±2 bloków), więc cała ikona trafia w jedną warstwę
        bool list = Position.z < -15.0;
        z = (list ? -0.99500 : -0.99330) - clamp(p.z + (list ? 80.0 : 40.0), -8.0, 8.0) * 0.000005;
    }
    gl_Position = axonGsClip(canvas, z);
    vec3 key = normalize(vec3(-0.45, 0.80, 0.55));
    vec3 fill = normalize(vec3(0.70, 0.15, 0.45));
    float l = 0.36 + 0.60 * max(dot(n, key), 0.0) + 0.20 * max(dot(n, fill), 0.0);
    float rim = pow(1.0 - abs(n.z), 2.0) * max(n.y, 0.0) * 0.18;
    vertexColor = vec4(Color.rgb * l + vec3(0.55, 0.85, 0.78) * rim, Color.a);
    return true;
}
