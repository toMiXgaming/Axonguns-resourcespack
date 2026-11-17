// Menu akcesoriów AxonGuns, fragment elementów z axon_gs_ui.glsl (axonHud == 22).
const vec3 AXON_GS_GROUP[4] = vec3[4](vec3(110.0, 220.0, 190.0) / 255.0, vec3(240.0, 160.0, 90.0) / 255.0,
        vec3(110.0, 160.0, 240.0) / 255.0, vec3(240.0, 200.0, 110.0) / 255.0);

vec4 axonGsUiOver(vec4 top, vec4 under) {
    float a = top.a + under.a * (1.0 - top.a);
    return vec4((top.rgb * top.a + under.rgb * under.a * (1.0 - top.a)) / max(a, 1e-4), a);
}

// narożniki „taktyczne”: krótkie L w rogach kafelka
float axonGsCorners(vec2 p, vec2 size, float len, float aa) {
    vec2 q = min(p, size - p);
    float edge = 1.0 - smoothstep(0.6, 0.6 + aa, min(q.x, q.y));
    float inCorner = step(min(q.x, q.y), 1.2) * step(max(q.x, q.y), len);
    return edge * inCorner;
}

vec4 axonGsUiBox() {
    vec2 size = axonHudBox.xy;
    int kind = int(axonHudBox.z + 0.5);
    int state = int(axonHudBox.w + 0.5);
    int pp = int(axonHudExtra.z + 0.5);
    float show = axonHudExtra.w;
    vec2 p = axonHudLocal;
    vec2 cur = axonCursor * vec2(640.0, 384.0) - axonHudExtra.xy;
    bool hot = cur.x >= 0.0 && cur.y >= 0.0 && cur.x < size.x && cur.y < size.y;
    float aa = max(fwidth(p.x), 1e-3);
    float v = clamp(p.y / max(size.y, 1.0), 0.0, 1.0);
    vec3 acc = vec3(110.0, 220.0, 190.0) / 255.0;
    vec4 o;

    if (kind == 3) {
        // pasek: tor z podziałką co 10 %, biała wartość, zmiana na zielono (lepiej) albo czerwono (gorzej)
        float base = axonHudAcc2.x;
        float target = axonHudAcc2.y;
        float prog = axonHudAcc2.z;
        float d = axonRoundBox(p - size * 0.5, size * 0.5, 1.5);
        float inside = 1.0 - smoothstep(-aa, aa, d);
        float x = p.x / size.x;
        float tick = 1.0 - smoothstep(0.0, aa * 1.5, abs(fract(x * 10.0 + 0.5) - 0.5) * size.x * 0.1 - 0.35);
        vec3 col = vec3(0.19, 0.21, 0.26);
        float alpha = 0.9;
        float lo = min(base, target);
        float now = target >= base ? base + (target - base) * prog : base - (base - target) * prog;
        if (x < min(base, now)) {
            col = vec3(0.88, 0.91, 0.95);
        } else if (target > base && x < now) {
            col = vec3(0.36, 0.86, 0.46);
        } else if (target < base && x >= now && x < base) {
            col = vec3(0.96, 0.42, 0.38);
        }
        col = mix(col, col * 0.55, tick * step(0.02, x) * step(x, 0.98));
        o = vec4(col, inside * alpha);
        return o;
    }

    float r = kind == 2 ? 3.0 : (kind == 1 ? 5.0 : 4.0);
    float d = axonRoundBox(p - size * 0.5, size * 0.5, r);
    float inside = 1.0 - smoothstep(-aa, aa, d);
    float border = inside * (1.0 - smoothstep(0.0, 1.0 + aa, -d));
    vec4 shadow = vec4(0.0, 0.0, 0.0, 0.35 * (1.0 - smoothstep(-1.0, 7.0, d - 1.5)));

    if (kind == 0) {
        bool sel = state == 1;
        bool empty = state == 2;
        vec3 grp = AXON_GS_GROUP[pp];
        vec3 fill = mix(vec3(0.115, 0.13, 0.16), vec3(0.07, 0.08, 0.10), v);
        if (sel) fill = mix(fill, acc * 0.35, 0.45);
        if (hot && !sel) fill += vec3(0.035);
        float fa = empty ? 0.72 : 0.93;
        vec3 edge = sel ? acc : (hot ? vec3(0.45, 0.50, 0.58) : vec3(0.24, 0.27, 0.33));
        o = vec4(mix(fill, edge, border), inside * fa);
        // pasek grupy po lewej
        float stripe = inside * (1.0 - smoothstep(2.0, 2.0 + aa, p.x)) * step(5.0, p.y) * step(p.y, size.y - 5.0);
        o.rgb = mix(o.rgb, grp, stripe * (empty ? 0.45 : 1.0));
        // narożniki
        float cn = axonGsCorners(p, size, 6.0, aa);
        o.rgb = mix(o.rgb, sel ? vec3(1.0) : grp * 1.1, cn * (empty ? 0.35 : 0.85));
        // górna poświata
        o.rgb += (sel ? acc * 0.12 : vec3(0.03)) * (1.0 - smoothstep(0.0, 10.0, p.y)) * inside;
        vec4 glow = sel ? vec4(acc, 0.28 * (1.0 - smoothstep(0.0, 7.0, d))) : vec4(0.0);
        return axonGsUiOver(o, axonGsUiOver(glow, shadow));
    }

    if (kind == 1) {
        vec3 fill = mix(vec3(0.075, 0.085, 0.105), vec3(0.05, 0.055, 0.07), v);
        vec3 edge = vec3(0.27, 0.30, 0.36);
        o = vec4(mix(fill, edge, border), inside * 0.97);
        // akcent u góry
        float top = inside * (1.0 - smoothstep(1.0, 1.0 + aa, p.y)) * step(6.0, p.x) * step(p.x, size.x - 6.0);
        o.rgb = mix(o.rgb, acc, top);
        return axonGsUiOver(o, shadow);
    }

    // kind 2: wiersz listy
    bool missing = state == 2;
    bool worn = state == 1;
    bool remove = state == 3;
    bool can = !missing;
    vec3 hl = remove ? vec3(0.96, 0.45, 0.40) : acc;
    float hov = hot && can ? 1.0 : 0.0;
    o = vec4(hl, inside * (0.16 * hov + (worn ? 0.07 : 0.0)));
    o.rgb = mix(o.rgb, hl, border * hov);
    o.a = max(o.a, border * hov * 0.9);
    float bar = inside * (1.0 - smoothstep(2.0, 2.0 + aa, p.x)) * step(4.0, p.y) * step(p.y, size.y - 4.0);
    if (worn) {
        o = axonGsUiOver(vec4(acc, bar), o);
    }
    return o;
}
