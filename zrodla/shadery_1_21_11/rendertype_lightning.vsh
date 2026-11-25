#version 330

// Ta sama pozycja co w innych shaderach, bit w bit (inaczej napis z daleka przeplata się z deską tabliczki).
invariant gl_Position;

#moj_import <minecraft:fog.glsl>
#moj_import <minecraft:dynamictransforms.glsl>
#moj_import <minecraft:projection.glsl>
#moj_import <minecraft:globals.glsl>
#moj_import <minecraft:axon_freeze.glsl>

in vec3 Position;
in vec4 Color;

out float sphericalVertexDistance;
out float cylindricalVertexDistance;
out vec4 vertexColor;

void main() {
    gl_Position = axonWorldProj(ProjMat) * axonWorldView(ModelViewMat, ProjMat) * vec4(Position, 1.0);

    sphericalVertexDistance = fog_spherical_distance(Position);
    cylindricalVertexDistance = fog_cylindrical_distance(Position);
    vertexColor = Color;
}
