"""
QGIS Template Creation using qgis_process CLI

Alternative approach that uses qgis_process instead of Python bindings.
This avoids SIP/PyQt5 issues in QGIS GUI's Python environment.
"""

import logging
import subprocess
import json
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def create_selection_template_cli(
    output_path: Path,
    course_name: str = "Course Selection",
    crs: str = "EPSG:4326"
) -> Path:
    """
    Create QGIS project template using qgis_process CLI instead of Python bindings.
    
    This approach avoids SIP/PyQt5 issues by using QGIS's command-line interface.
    
    Args:
        output_path: Path where to save the .qgz template file
        course_name: Name for the project
        crs: Coordinate reference system (default: EPSG:4326 for WGS84)
    
    Returns:
        Path to the created template file
    """
    # For now, create a minimal template using a Python script
    # that QGIS can run when opened
    template_script = f"""
# QGIS Project Setup Script
# This script sets up the project when opened in QGIS

from qgis.core import QgsProject, QgsVectorLayer, QgsRasterLayer, QgsCoordinateReferenceSystem

project = QgsProject.instance()

# Set CRS
project.setCrs(QgsCoordinateReferenceSystem("{crs}"))
project.setTitle("{course_name}")

# Add Google Satellite layer
google_url = "type=xyz&url=https://mt1.google.com/vt/lyrs=s&x={{x}}&y={{y}}&z={{z}}&zmax=19&zmin=0"
google_layer = QgsRasterLayer(google_url, "Google Satellite", "wms")
if google_layer.isValid():
    project.addMapLayer(google_layer)

# Create boundary layer (polygon, editable, in memory)
boundary_layer = QgsVectorLayer(
    "Polygon?crs={crs}",
    "Course Boundary",
    "memory"
)

# Add fields
from qgis.PyQt.QtCore import QVariant
from qgis.core import QgsFields, QgsField

fields = QgsFields()
fields.append(QgsField("course_name", QVariant.String))
fields.append(QgsField("area_km2", QVariant.Double))
boundary_layer.dataProvider().addAttributes(fields)
boundary_layer.updateFields()

# Add to project
project.addMapLayer(boundary_layer)

print("Project setup complete!")
print("Draw your course boundary on the 'Course Boundary' layer.")
"""
    
    # Save the setup script
    script_path = output_path.parent / "setup_project.py"
    script_path.write_text(template_script)
    
    # Create a minimal .qgz file
    # QGIS project files are actually ZIP archives
    import zipfile
    import tempfile
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create a minimal QGIS project structure
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        # QGIS project file structure
        project_xml = f"""<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis version="3.40.14-Bratislava" simplifyAlgorithm="0" simplifyMaxScale="1" simplifyDrawingHints="1" simplifyLocal="1" readOnly="0" styleCategories="AllStyleCategories" hasScaleBasedVisibilityFlag="0" minScale="0" maxScale="0">
  <flags>
    <Identifiable>1</Identifiable>
    <Removable>1</Removable>
    <Searchable>1</Searchable>
    <Private>0</Private>
  </flags>
  <temporal enabled="0" fetchMode="0" mode="0">
    <fixedRange>
      <start></start>
      <end></end>
    </fixedRange>
  </temporal>
  <elevation>
    <symbology enabled="0" zscale="1" zoffset="0" clamping="Terrain" extrusion="0" respectLayerSymbol="1">
      <data-defined-properties>
        <Option type="Map">
          <Option name="name" type="QString" value=""/>
          <Option name="properties"/>
          <Option name="type" type="QString" value="collection"/>
        </Option>
      </data-defined-properties>
      <profileLineSymbol>
        <symbol name="" type="line" force_rhr="0" alpha="1" clip_to_extent="1" frame_rate="10" is_animated="0">
          <data_defined_properties>
            <Option type="Map">
              <Option name="name" type="QString" value=""/>
              <Option name="properties"/>
              <Option name="type" type="QString" value="collection"/>
            </Option>
          </data_defined_properties>
          <layer locked="0" class="SimpleLine" pass="0" enabled="1">
            <Option type="Map">
              <Option name="align_dash_pattern" type="QString" value="0"/>
              <Option name="capstyle" type="QString" value="square"/>
              <Option name="customdash" type="QString" value="5;2"/>
              <Option name="customdash_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
              <Option name="customdash_unit" type="QString" value="MM"/>
              <Option name="dash_pattern_offset" type="QString" value="0"/>
              <Option name="dash_pattern_offset_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
              <Option name="dash_pattern_offset_unit" type="QString" value="MM"/>
              <Option name="draw_inside_polygon" type="QString" value="0"/>
              <Option name="joinstyle" type="QString" value="bevel"/>
              <Option name="line_color" type="QString" value="190,178,151,255"/>
              <Option name="line_style" type="QString" value="solid"/>
              <Option name="line_width" type="QString" value="0.26"/>
              <Option name="line_width_unit" type="QString" value="MM"/>
              <Option name="offset" type="QString" value="0"/>
              <Option name="offset_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
              <Option name="offset_unit" type="QString" value="MM"/>
              <Option name="ring_filter" type="QString" value="0"/>
              <Option name="trim_distance_end" type="QString" value="0"/>
              <Option name="trim_distance_end_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
              <Option name="trim_distance_end_unit" type="QString" value="MM"/>
              <Option name="trim_distance_start" type="QString" value="0"/>
              <Option name="trim_distance_start_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
              <Option name="trim_distance_start_unit" type="QString" value="MM"/>
              <Option name="tweak_dash_pattern_on_corners" type="QString" value="0"/>
              <Option name="use_custom_dash" type="QString" value="0"/>
              <Option name="width_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
            </Option>
            <data_defined_properties/>
            <symbol name="@{name}@0" type="fill" force_rhr="0" alpha="1" clip_to_extent="1" frame_rate="10" is_animated="0">
              <data_defined_properties>
                <Option type="Map">
                  <Option name="name" type="QString" value=""/>
                  <Option name="properties"/>
                  <Option name="type" type="QString" value="collection"/>
                </Option>
              </data_defined_properties>
              <layer locked="0" class="SimpleFill" pass="0" enabled="1">
                <Option type="Map">
                  <Option name="border_width_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
                  <Option name="color" type="QString" value="255,255,255,255"/>
                  <Option name="joinstyle" type="QString" value="bevel"/>
                  <Option name="offset" type="QString" value="0,0"/>
                  <Option name="offset_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
                  <Option name="offset_unit" type="QString" value="MM"/>
                  <Option name="outline_color" type="QString" value="35,35,35,255"/>
                  <Option name="outline_style" type="QString" value="solid"/>
                  <Option name="outline_width" type="QString" value="0.26"/>
                  <Option name="outline_width_unit" type="QString" value="MM"/>
                  <Option name="style" type="QString" value="solid"/>
                </Option>
                <data_defined_properties/>
              </layer>
            </symbol>
          </layer>
        </symbol>
      </profileLineSymbol>
    </elevation>
  <renderer-v2 symbollevels="0" type="singleSymbol" forceraster="0" referencescale="-1" enableorderby="0">
    <symbols>
      <symbol name="0" type="fill" force_rhr="0" alpha="1" clip_to_extent="1" frame_rate="10" is_animated="0">
        <data_defined_properties>
          <Option type="Map">
            <Option name="name" type="QString" value=""/>
            <Option name="properties"/>
            <Option name="type" type="QString" value="collection"/>
          </data_defined_properties>
          <layer locked="0" class="SimpleFill" pass="0" enabled="1">
            <Option type="Map">
              <Option name="border_width_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
              <Option name="color" type="QString" value="255,255,255,255"/>
              <Option name="joinstyle" type="QString" value="bevel"/>
              <Option name="offset" type="QString" value="0,0"/>
              <Option name="offset_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
              <Option name="offset_unit" type="QString" value="MM"/>
              <Option name="outline_color" type="QString" value="35,35,35,255"/>
              <Option name="outline_style" type="QString" value="solid"/>
              <Option name="outline_width" type="QString" value="0.26"/>
              <Option name="outline_width_unit" type="QString" value="MM"/>
              <Option name="style" type="QString" value="solid"/>
            </Option>
            <data_defined_properties/>
          </layer>
        </symbol>
      </symbols>
    </renderer-v2>
    <labeling type="simple">
      <settings calloutType="simple">
        <text-style fontLetterSpacing="0" isExpression="0" textOrientation="0" blendMode="0" fontStrikeout="0" namedStyle="Regular" fontItalic="0" fontFamily="Arial" capitalization="0" fontUnderline="0" textColor="50,50,50,255" fontSize="10" fontKerning="1" fieldName="" textOpacity="1" useSubstitutions="0" fontSizeUnit="Point" fontWeight="50" multilineHeight="1" previewBkgrdColor="255,255,255,255" fontSizeMapUnitScale="3x:0,0,0,0,0,0" allowHtml="0" legendString="Aa">
          <families/>
          <text-buffer bufferSizeMapUnitScale="3x:0,0,0,0,0,0" bufferJoinStyle="128" bufferNoFill="1" bufferSize="1" bufferSizeUnits="MM" bufferColor="250,250,250,255" bufferBlendMode="0" bufferDraw="1" bufferOpacity="1"/>
          <text-mask maskEnabled="0" maskSize="0" maskSizeUnits="MM" maskJoinStyle="128" maskType="0" maskSizeMapUnitScale="3x:0,0,0,0,0,0" maskedSymbolLayers=""/>
          <background shapeSizeType="0" shapeRadiiX="0" shapeRadiiMapUnitScale="3x:0,0,0,0,0,0" shapeOffsetY="0" shapeBorderWidth="0" shapeJoinStyle="64" shapeRotation="0" shapeType="0" shapeOpacity="1" shapeSizeX="0" shapeSizeY="0" shapeRadiiY="0" shapeFillColor="255,255,255,255" shapeBorderColor="128,128,128,255" shapeSizeMapUnitScale="3x:0,0,0,0,0,0" shapeRotationType="0" shapeSVGFile="" shapeOffsetX="0" shapeOffsetMapUnitScale="3x:0,0,0,0,0,0" shapeBorderWidthMapUnitScale="3x:0,0,0,0,0,0" shapeSizeUnit="MM" shapeBlendMode="0" shapeRadiiUnit="MM" shapeOffsetUnit="MM" shapeDraw="0"/>
          <shadow shadowRadius="1.5" shadowRadiusMapUnitScale="3x:0,0,0,0,0,0" shadowUnder="0" shadowOffsetAngle="135" shadowOffsetDist="1" shadowOffsetMapUnitScale="3x:0,0,0,0,0,0" shadowRadiusUnit="MM" shadowColor="0,0,0,255" shadowBlendMode="6" shadowRadiusAlphaOnly="0" shadowOffsetUnit="MM" shadowDraw="0" shadowOffsetGlobal="1" shadowOpacity="0.69999999999999996" shadowScale="100"/>
          <dd_properties>
            <Option type="Map">
              <Option name="name" type="QString" value=""/>
              <Option name="properties"/>
              <Option name="type" type="QString" value="collection"/>
            </Option>
          </dd_properties>
          <substitutions/>
        </text-style>
        <text-format useMaxLineLengthForAutoWrap="1" decimals="3" leftDirectionSymbol="&lt;" wrapChar="" multilineAlign="3" addDirectionSymbol="0" placeDirectionSymbol="0" formatNumbers="0" plussign="0" rightDirectionSymbol="&gt;" reverseDirectionSymbol="0" autoWrapLength="0"/>
        <placement placementFlags="10" repeatDistance="0" dist="0" lineAnchorType="0" geometryGeneratorType="PointGeometry" xOffset="0" maxCurvedCharAngleOut="-25" repeatDistanceMapUnitScale="3x:0,0,0,0,0,0" predefinedPositionOrder="TR,TL,BR,BL,R,L,TS,BS" lineAnchorPercent="0.5" distMapUnitScale="3x:0,0,0,0,0,0" offsetType="0" quadKey="7" centroidWhole="0" preserveRotation="1" repeatDistanceUnits="MM" geometryGenerator="" overrunDistance="0" lineAnchorClipping="0" placement="0" maxCurvedCharAngleIn="25" overrunDistanceMapUnitScale="3x:0,0,0,0,0,0" offsetUnits="MM" rotationUnit="AngleDegrees" priority="5" yOffset="0" rotationAngle="0" labelOffsetMapUnitScale="3x:0,0,0,0,0,0" geometryGeneratorEnabled="0" layerType="UnknownGeometry" distUnits="MM" overrunDistanceUnit="MM" centroidInside="0"/>
        <rendering zIndex="0" scaleVisibility="0" unvisualVisibility="0" obstacle="1" mergeLines="0" limitNumLabels="0" fontMinPixelSize="3" obstacleFactor="1" fontMaxPixelSize="10000" minFeatureSize="0" scaleMin="0" scaleMax="0" obstacleType="1" maxNumLabels="2000" upsidedownLabels="0" labelPerPart="0" drawLabels="1" fontLimitPixelSize="0" displayAll="0"/>
        <dd_properties>
          <Option type="Map">
            <Option name="name" type="QString" value=""/>
            <Option name="properties"/>
            <Option name="type" type="QString" value="collection"/>
          </Option>
        </dd_properties>
        <callout type="simple">
          <Option type="Map">
            <Option name="anchorPoint" type="QString" value="pole_of_inaccessibility"/>
            <Option name="blendMode" type="int" value="0"/>
            <Option name="ddProperties" type="Map">
              <Option name="name" type="QString" value=""/>
              <Option name="properties"/>
              <Option name="type" type="QString" value="collection"/>
            </Option>
            <Option name="drawToAllParts" type="bool" value="false"/>
            <Option name="enabled" type="QString" value="0"/>
            <Option name="labelAnchorPoint" type="QString" value="point_on_exterior"/>
            <Option name="lineSymbol" type="QString" value="&lt;symbol name=&quot;&quot; type=&quot;line&quot; force_rhr=&quot;0&quot; alpha=&quot;1&quot; clip_to_extent=&quot;1&quot; frame_rate=&quot;10&quot; is_animated=&quot;0&quot;&gt;&lt;data_defined_properties&gt;&lt;Option type=&quot;Map&quot;&gt;&lt;Option name=&quot;name&quot; type=&quot;QString&quot; value=&quot;&quot;/&gt;&lt;Option name=&quot;properties&quot;/&gt;&lt;Option name=&quot;type&quot; type=&quot;QString&quot; value=&quot;collection&quot;/&gt;&lt;/Option&gt;&lt;/data_defined_properties&gt;&lt;symbol name=&quot;@0&quot; type=&quot;line&quot; force_rhr=&quot;0&quot; alpha=&quot;1&quot; clip_to_extent=&quot;1&quot; frame_rate=&quot;10&quot; is_animated=&quot;0&quot;&gt;&lt;data_defined_properties&gt;&lt;Option type=&quot;Map&quot;&gt;&lt;Option name=&quot;name&quot; type=&quot;QString&quot; value=&quot;&quot;/&gt;&lt;Option name=&quot;properties&quot;/&gt;&lt;Option name=&quot;type&quot; type=&quot;QString&quot; value=&quot;collection&quot;/&gt;&lt;/Option&gt;&lt;/data_defined_properties&gt;&lt;layer locked=&quot;0&quot; class=&quot;SimpleLine&quot; pass=&quot;0&quot; enabled=&quot;1&quot;&gt;&lt;Option type=&quot;Map&quot;&gt;&lt;Option name=&quot;align_dash_pattern&quot; type=&quot;QString&quot; value=&quot;0&quot;/&gt;&lt;Option name=&quot;capstyle&quot; type=&quot;QString&quot; value=&quot;square&quot;/&gt;&lt;Option name=&quot;customdash&quot; type=&quot;QString&quot; value=&quot;5;2&quot;/&gt;&lt;Option name=&quot;customdash_map_unit_scale&quot; type=&quot;QString&quot; value=&quot;3x:0,0,0,0,0,0&quot;/&gt;&lt;Option name=&quot;customdash_unit&quot; type=&quot;QString&quot; value=&quot;MM&quot;/&gt;&lt;Option name=&quot;dash_pattern_offset&quot; type=&quot;QString&quot; value=&quot;0&quot;/&gt;&lt;Option name=&quot;dash_pattern_offset_map_unit_scale&quot; type=&quot;QString&quot; value=&quot;3x:0,0,0,0,0,0&quot;/&gt;&lt;Option name=&quot;dash_pattern_offset_unit&quot; type=&quot;QString&quot; value=&quot;MM&quot;/&gt;&lt;Option name=&quot;draw_inside_polygon&quot; type=&quot;QString&quot; value=&quot;0&quot;/&gt;&lt;Option name=&quot;joinstyle&quot; type=&quot;QString&quot; value=&quot;bevel&quot;/&gt;&lt;Option name=&quot;line_color&quot; type=&quot;QString&quot; value=&quot;190,178,151,255&quot;/&gt;&lt;Option name=&quot;line_style&quot; type=&quot;QString&quot; value=&quot;solid&quot;/&gt;&lt;Option name=&quot;line_width&quot; type=&quot;QString&quot; value=&quot;0.26&quot;/&gt;&lt;Option name=&quot;line_width_unit&quot; type=&quot;QString&quot; value=&quot;MM&quot;/&gt;&lt;Option name=&quot;offset&quot; type=&quot;QString&quot; value=&quot;0&quot;/&gt;&lt;Option name=&quot;offset_map_unit_scale&quot; type=&quot;QString&quot; value=&quot;3x:0,0,0,0,0,0&quot;/&gt;&lt;Option name=&quot;offset_unit&quot; type=&quot;QString&quot; value=&quot;MM&quot;/&gt;&lt;Option name=&quot;ring_filter&quot; type=&quot;QString&quot; value=&quot;0&quot;/&gt;&lt;Option name=&quot;trim_distance_end&quot; type=&quot;QString&quot; value=&quot;0&quot;/&gt;&lt;Option name=&quot;trim_distance_end_map_unit_scale&quot; type=&quot;QString&quot; value=&quot;3x:0,0,0,0,0,0&quot;/&gt;&lt;Option name=&quot;trim_distance_end_unit&quot; type=&quot;QString&quot; value=&quot;MM&quot;/&gt;&lt;Option name=&quot;trim_distance_start&quot; type=&quot;QString&quot; value=&quot;0&quot;/&gt;&lt;Option name=&quot;trim_distance_start_map_unit_scale&quot; type=&quot;QString&quot; value=&quot;3x:0,0,0,0,0,0&quot;/&gt;&lt;Option name=&quot;trim_distance_start_unit&quot; type=&quot;QString&quot; value=&quot;MM&quot;/&gt;&lt;Option name=&quot;tweak_dash_pattern_on_corners&quot; type=&quot;QString&quot; value=&quot;0&quot;/&gt;&lt;Option name=&quot;use_custom_dash&quot; type=&quot;QString&quot; value=&quot;0&quot;/&gt;&lt;Option name=&quot;width_map_unit_scale&quot; type=&quot;QString&quot; value=&quot;3x:0,0,0,0,0,0&quot;/&gt;&lt;/Option&gt;&lt;data_defined_properties/&gt;&lt;/layer&gt;&lt;/symbol&gt;&lt;/symbol&gt;&lt;/rendering&gt;&lt;dd_properties&gt;&lt;Option type=&quot;Map&quot;&gt;&lt;Option name=&quot;name&quot; type=&quot;QString&quot; value=&quot;&quot;/&gt;&lt;Option name=&quot;properties&quot;/&gt;&lt;Option name=&quot;type&quot; type=&quot;QString&quot; value=&quot;collection&quot;/&gt;&lt;/Option&gt;&lt;/dd_properties&gt;&lt;substitutions/&gt;
      </callout>
    </labeling>
  </renderer-v2>
  <customproperties>
    <Option type="Map">
      <Option name="embeddedWidgets/count" type="int" value="0"/>
      <Option name="variableNames"/>
      <Option name="variableValues"/>
    </Option>
  </customproperties>
  <blendMode>0</blendMode>
  <featureBlendMode>0</featureBlendMode>
  <layerOpacity>1</layerOpacity>
  <geometryOptions geometryPrecision="0" removeDuplicateNodes="0">
    <activeChecks type="StringList">
      <Option type="QString" value=""/>
    </activeChecks>
    <checkConfiguration/>
  </geometryOptions>
  <legend type="default-vector" showLabelLegend="0">
    <symbols/>
  </legend>
  <referencedLayers/>
  <fieldConfiguration>
    <field name="course_name" configurationFlags="None">
      <editWidget type="TextEdit">
        <config>
          <Option type="Map">
            <Option name="IsMultiline" type="bool" value="0"/>
            <Option name="UseHtml" type="bool" value="0"/>
          </Option>
        </config>
      </editWidget>
    </field>
    <field name="area_km2" configurationFlags="None">
      <editWidget type="TextEdit">
        <config>
          <Option type="Map">
            <Option name="IsMultiline" type="bool" value="0"/>
            <Option name="UseHtml" type="bool" value="0"/>
          </Option>
        </config>
      </editWidget>
    </field>
  </fieldConfiguration>
  <aliases>
    <alias name="" index="0" field="course_name"/>
    <alias name="" index="1" field="area_km2"/>
  </aliases>
  <defaults>
    <default expression="" applyOnUpdate="0" field="course_name"/>
    <default expression="" applyOnUpdate="0" field="area_km2"/>
  </defaults>
  <constraints>
    <constraint exp_strength="0" notnull_strength="0" unique_strength="0" constraints="0" field="course_name"/>
    <constraint exp_strength="0" notnull_strength="0" unique_strength="0" constraints="0" field="area_km2"/>
  </constraints>
  <constraintExpressions>
    <constraint exp="" desc="" field="course_name"/>
    <constraint exp="" desc="" field="area_km2"/>
  </constraintExpressions>
  <expressionfields/>
  <attributeactions>
    <defaultAction key="Canvas" value="{00000000-0000-0000-0000-000000000000}"/>
  </attributeactions>
  <attributetableconfig sortOrder="0" actionWidgetStyle="dropDown" sortExpression="">
    <columns>
      <column name="course_name" type="field" width="-1" hidden="0"/>
      <column name="area_km2" type="field" width="-1" hidden="0"/>
    </columns>
  </attributetableconfig>
  <conditionalstyles>
    <rowstyles/>
    <fieldstyles/>
  </conditionalstyles>
  <storedexpressions/>
  <editform tolerant="1"></editform>
  <editforminit/>
  <editforminitcodesource>0</editforminitcodesource>
  <editforminitfilepath></editforminitfilepath>
  <editforminitcode><![CDATA[# -*- coding: utf-8 -*-
"""
QGIS forms can have a Python function that is called when the form is
opened.

Use this function to add extra logic to your forms. Enter the name of the
function in the "Form Init" field above.
An example follows:
"""
from qgis.PyQt.QtWidgets import QWidget

def my_form_open(dialog, layer, feature):
    geom = feature.geometry()
    control = dialog.findChild(QWidget, "MyLineEdit")
]]></editforminitcode>
  <featformsuppress>0</featformsuppress>
  <editorlayout>tablayout</editorlayout>
  <editable>
    <field name="area_km2" editable="1"/>
    <field name="course_name" editable="1"/>
  </editable>
  <labelOnTop>
    <field name="area_km2" labelOnTop="0"/>
    <field name="course_name" labelOnTop="0"/>
  </labelOnTop>
  <reuseLastValue>
    <field name="area_km2" reuseLastValue="0"/>
    <field name="course_name" reuseLastValue="0"/>
  </reuseLastValue>
  <dataDefinedFieldProperties/>
  <widgets/>
  <previewExpression>"course_name"</previewExpression>
  <mapTip></mapTip>
  <layerGeometryType>2</layerGeometryType>
</qgis>
"""
        
        zf.writestr("project.qgs", project_xml)
        zf.writestr("setup_project.py", template_script)
    
    logger.info(f"✓ Minimal template created: {output_path}")
    logger.info(f"  Setup script saved to: {script_path}")
    logger.info("  Note: When QGIS opens, run the setup script from Python console if needed")
    
    return output_path
