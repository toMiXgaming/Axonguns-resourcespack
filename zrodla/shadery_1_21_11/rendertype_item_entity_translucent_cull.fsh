#version 330

#moj_import <minecraft:fog.glsl>
#moj_import <minecraft:dynamictransforms.glsl>
#moj_import <minecraft:globals.glsl>

uniform sampler2D Sampler0;

in float sphericalVertexDistance;
in float cylindricalVertexDistance;
in vec4 vertexColor;
in vec2 texCoord0;
in vec2 texCoord1;
flat in vec4 axonGsA;
flat in vec4 axonGsB;
in vec2 axonGsP;

out vec4 fragColor;

#moj_import <minecraft:axon_gs.glsl>
#moj_import <minecraft:axon_gs_link.glsl>

void main() {
    if (axonGsA.x > 0.5) {
        // linia menu akcesoriów AxonGuns
        fragColor = axonGsLink();
        if (fragColor.a < 0.004) {
            discard;
        }
        return;
    }
    vec4 color = texture(Sampler0, texCoord0) * vertexColor * ColorModulator;
    if (color.a < 0.1) {
        discard;
    }
    fragColor = apply_fog(color, sphericalVertexDistance, cylindricalVertexDistance, FogEnvironmentalStart, FogEnvironmentalEnd, FogRenderDistanceStart, FogRenderDistanceEnd, FogColor);
}
