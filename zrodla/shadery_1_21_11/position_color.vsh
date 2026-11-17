#version 330

#moj_import <minecraft:dynamictransforms.glsl>
#moj_import <minecraft:projection.glsl>
#moj_import <minecraft:globals.glsl>
#moj_import <minecraft:axon_freeze.glsl>

in vec3 Position;
in vec4 Color;

out vec4 vertexColor;

void main() {
    gl_Position = axonWorldProj(ProjMat) * axonWorldView(ModelViewMat, ProjMat) * vec4(Position, 1.0);

    vertexColor = Color;
}
