// Fragment linii menu AxonGuns (axon_gs_item.glsl): linia od kafelka, kropka na broni.
// axonGsA = (1, założone | wybrane << 1, kropka.xy), axonGsB = (kafelek.xy, postęp rysowania, 0).
vec4 axonGsOver(vec4 top, vec4 under) {
    float a = top.a + under.a * (1.0 - top.a);
    return vec4((top.rgb * top.a + under.rgb * under.a * (1.0 - top.a)) / max(a, 1e-4), a);
}

vec4 axonGsLink() {
    vec2 p = axonGsP;
    vec2 a = axonGsB.xy;
    vec2 b = axonGsA.zw;
    int flags = int(axonGsA.y + 0.5);
    bool filled = (flags & 1) != 0;
    bool sel = (flags & 2) != 0;
    float aa = max(fwidth(p.x), 1e-3);
    float t = axonGsB.z;
    t = t * t * (3.0 - 2.0 * t);
    vec3 acc = vec3(110.0, 220.0, 190.0) / 255.0;
    vec3 grey = vec3(0.62, 0.66, 0.73);
    float r = sel ? 3.6 : 3.0;
    vec2 dir = normalize(b - a);
    // linia rośnie od kafelka do kropki, kończy się na krawędzi kropki
    vec2 end = mix(a, b - dir * (r + 1.0), t);
    vec2 pa = p - a, ba = end - a;
    float h = clamp(dot(pa, ba) / max(dot(ba, ba), 1e-4), 0.0, 1.0);
    float d = length(pa - ba * h);
    float lw = sel ? 0.75 : 0.5;
    float line = 1.0 - smoothstep(lw - aa * 0.5, lw + aa, d);
    vec4 o = vec4(sel ? acc : grey, line * (sel ? 0.9 : 0.5));
    // kropka pojawia się pod koniec rysowania linii
    float show = smoothstep(0.75, 1.0, t);
    float pulse = 0.5 + 0.5 * sin(axonGsPhase() * 2.0);
    float dc = length(p - b);
    vec3 col = filled || sel ? acc : grey;
    float ring = 1.0 - smoothstep(r - aa, r + aa, dc);
    float hole = filled ? 0.0 : 1.0 - smoothstep(r - 1.4 - aa, r - 1.4 + aa, dc);
    vec4 knob = vec4(mix(col, vec3(0.06, 0.07, 0.09), hole * 0.85), ring * show);
    if (filled) knob.rgb = mix(knob.rgb, vec3(1.0), (1.0 - smoothstep(0.0, r * 0.6, dc)) * 0.35);
    float glowR = r + (sel ? 3.0 + 2.5 * pulse : 2.5);
    float glow = (1.0 - smoothstep(r, glowR, dc)) * (sel ? 0.45 : (filled ? 0.25 + 0.1 * pulse : 0.0)) * show;
    // ciemna obwódka pod kropką, żeby było ją widać na jasnych częściach broni
    vec4 shade = vec4(0.02, 0.03, 0.04, (1.0 - smoothstep(r + 0.4, r + 1.6, dc)) * show * 0.55);
    vec4 outc = axonGsOver(vec4(col, glow), shade);
    outc = axonGsOver(o, outc);
    return axonGsOver(knob, outc);
}
