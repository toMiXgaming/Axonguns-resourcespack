#version 330

// Ta sama pozycja co w innych shaderach, bit w bit (inaczej napis z daleka przeplata się z deską tabliczki).
invariant gl_Position;

#moj_import <minecraft:dynamictransforms.glsl>
#moj_import <minecraft:projection.glsl>
#moj_import <minecraft:globals.glsl>
#moj_import <minecraft:axon_freeze.glsl>

in vec3 Position;
in vec2 UV0;

out vec2 texCoord0;

void main() {
    vec3 pos = Position + ModelOffset;
    gl_Position = axonWorldProj(ProjMat) * axonWorldView(ModelViewMat, ProjMat) * vec4(pos, 1.0);

    texCoord0 = (TextureMat * vec4(UV0, 0.0, 1.0)).xy;
}
