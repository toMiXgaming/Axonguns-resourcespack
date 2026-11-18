#version 150

#moj_import <minecraft:fog.glsl>

uniform sampler2D Sampler0;

uniform vec4 ColorModulator;
uniform float FogStart;
uniform float FogEnd;
uniform vec4 FogColor;
uniform float GameTime;

in float vertexDistance;
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
    fragColor = linear_fog(color, vertexDistance, FogStart, FogEnd, FogColor);
}
