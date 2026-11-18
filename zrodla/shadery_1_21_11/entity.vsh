#version 330

#moj_import <minecraft:light.glsl>
#moj_import <minecraft:fog.glsl>
#moj_import <minecraft:dynamictransforms.glsl>
#moj_import <minecraft:projection.glsl>
#moj_import <minecraft:globals.glsl>
#moj_import <minecraft:axon_freeze.glsl>
#moj_import <minecraft:axon_gs.glsl>

in vec3 Position;
in vec4 Color;
in vec2 UV0;
in ivec2 UV1;
in ivec2 UV2;
in vec3 Normal;

uniform sampler2D Sampler1;
uniform sampler2D Sampler2;

out float sphericalVertexDistance;
out float cylindricalVertexDistance;
#ifdef PER_FACE_LIGHTING
out vec4 vertexPerFaceColorBack;
out vec4 vertexPerFaceColorFront;
#else
out vec4 vertexColor;
#endif
out vec4 lightMapColor;
out vec4 overlayColor;
out vec2 texCoord0;

void main() {
    gl_Position = axonWorldProj(ProjMat) * axonWorldView(ModelViewMat, ProjMat) * vec4(Position, 1.0);

    sphericalVertexDistance = fog_spherical_distance(Position);
    cylindricalVertexDistance = fog_cylindrical_distance(Position);

#ifdef PER_FACE_LIGHTING
    vec2 light = minecraft_compute_light(Light0_Direction, Light1_Direction, Normal);
    vertexPerFaceColorBack = minecraft_mix_light_separate(-light, Color);
    vertexPerFaceColorFront = minecraft_mix_light_separate(light, Color);
#elif defined(NO_CARDINAL_LIGHTING)
    vertexColor = Color;
#else
    vertexColor = minecraft_mix_light(Light0_Direction, Light1_Direction, Normal, Color);
#endif
#ifndef EMISSIVE
    lightMapColor = texelFetch(Sampler2, UV2 / 16, 0);
#endif
    overlayColor = texelFetch(Sampler1, UV1, 0);

    // ikona przedmiotu-bloku na kaflu okna (ItemDisplay ze znacznikiem światła, jak ikony w axon_gs_item.glsl):
    // bloki rysują się shaderem encji, nie przedmiotu, więc tu też kładziemy je na płótno
    if (ProjMat[2][3] != 0.0 && UV2 == AXON_GS_ICON_LIGHT && axonGsTime()) {
        vec3 p = Position / AXON_GS_UNIT;
        bool list = Position.z < -15.0;
        float z = (list ? -0.99500 : -0.99330) - clamp(p.z + (list ? 80.0 : 40.0), -8.0, 8.0) * 0.000005;
        gl_Position = axonGsClip(vec2(320.0 + p.x, 192.0 - p.y), z);
        sphericalVertexDistance = 0.0;
        cylindricalVertexDistance = 0.0;
#ifndef EMISSIVE
        lightMapColor = vec4(1.0);
#endif
    }

    texCoord0 = UV0;
#ifdef APPLY_TEXTURE_MATRIX
    texCoord0 = (TextureMat * vec4(UV0, 0.0, 1.0)).xy;
#endif
}
