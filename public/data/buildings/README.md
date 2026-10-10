# NYC 建筑数据来源与加工记录

获取日期：2026-10-06（上海）；UTC时间、查询URL及哈希详见 source.json。

## 来源与使用条件

- 官方元数据：https://raw.githubusercontent.com/CityOfNewYork/nyc-geo-metadata/master/Metadata/Metadata_BuildingFootprints.md
- 官方服务：https://services6.arcgis.com/yG5s3afENB5iO9fj/arcgis/rest/services/BUILDING_view/FeatureServer/0
- 使用条款：https://data.cityofnewyork.us/stories/s/Terms-of-Use/k9k7-3cje
- 开放政策：https://cityofnewyork.github.io/opendatatsm/publicpolicies.html

适用NYC Open Data条款；保留来源和加工记录，信息用途且不保证准确性、时效性或完整性。未将其标注为CC0，也未宣称测绘认证。

查询包围盒：西-74.0105、南40.7060、东-74.0070、北40.7090，纽约金融区。选取相交轮廓，保留完整几何，不切断查询边缘建筑。
先查询数量54，再下载3条样本3742字节，估计全量67356字节；实际66361字节，54个唯一OBJECTID。
下载限制150条/2MB，未下载整城、未付费、未注册账号。原始记录不补造、不重复。

## 坐标和单位

官方元数据描述原始维护坐标为NY State Plane EPSG:2263（US survey foot）；当前服务空间参考EPSG:3857。
本次明确请求outSR=4326，所得GeoJSON为经度、纬度（度）。不可把维护坐标、服务坐标和本次响应坐标混为一谈。
使用pyproj always_xy，将WGS84经纬度投影到UTM18N EPSG:32618（米）。
局部原点经纬度(-74.00875,40.7075)，投影E0=583733.7262765672、N0=4506760.039148921。
Three.js局部坐标：x=E-E0，z=-(N-N0)，y为平地以上假设高度，单位米。
转换参数、原始轮廓及所有原始属性保留在nyc-local.json中；未沿用地震演示的归一化距离。

## 处理步骤与质量

1. 保存nyc-raw.geojson、nyc-sample.geojson与source.json；SHA256记录于清单。
2. 检查有限数值、地区范围、唯一ID和Shapely多边形拓扑；本次54条有效、0条跳过。
3. 投影到局部米制，保留内环与多部件；Three.js闭合拉伸体真正作为Raycaster障碍物。
4. 高度字段HEIGHT_ROOF及地面字段GROUND_ELEVATION单位未充分核实：不使用其值冒充米制实测高度。全部建筑假设10米、地面0米。
5. 生成12个建筑轮廓外的模拟目标（y=1.5米）、两组模拟观察方案；模拟标记保留。
6. 先验证3建筑样本，再54建筑完整街区。固定完整版本nyc-block-v1-94305d13003f。

无DEM、无真实立面开口和屋顶细节、无树木/临时设施，查询范围外建筑未知；源数据本身亦可能缺漏或过时。
拉伸体的封闭表面是简化建模结果，不是实测完整面。可见性是目标点单射线结果，不是整个建筑面积占比。
方案A第一个目标与观察点水平位置相同但高度不同，水平朝向下处于视野外；不是目标重合或“计算失败”。
不将方案比较作为安全或工程认证。若以后确认高度/地形或修改转换方法，应提升版本并重新测试、导出报告。
