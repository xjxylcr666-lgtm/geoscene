# USGS 数据快照来源

文件：`usgs-earthquakes-2025-01-01-to-07.geojson`

官方接口：[USGS Earthquake Catalog API](https://earthquake.usgs.gov/fdsnws/event/1/1)

查询条件：

```text
format=geojson
starttime=2025-01-01
endtime=2025-01-08
minmagnitude=5
orderby=magnitude
limit=8
```

保存离线快照是为了让演示可以重复运行，不因实时目录变化而失效。USGS 页面说明其地震
信息属于公共领域；事件链接和原始字段保留在每个目标的 `sourceData` 中。

注意：项目会把经纬度归一化为本地 Three.js 坐标。场景中的距离、视角和墙体遮挡只是
GeoScene 工具链演示，不是地理距离、地震风险或真实地形分析。
