(function() {

var App = window.App;

App.wgs84 = new OpenLayers.Projection("EPSG:4326");
App.webmerc = new OpenLayers.Projection("EPSG:900913");


App.map_point = function(lon, lat) {
    return new OpenLayers.LonLat(lon, lat).transform(App.wgs84, App.webmerc);
};


App.init = function() {
    var map = App.map = new OpenLayers.Map('map');
    map.addLayer(new OpenLayers.Layer.OSM());
    map.setCenter(App.map_point(25, 46), 7);
    map.addControl(new OpenLayers.Control.LayerSwitcher());

    var judete_layer = new OpenLayers.Layer.MapServer(
        "judete", App.MAPSERV_URL, {layers: 'judete'},
        {gutter: 15,
         projection: App.webmerc,
         isBaseLayer: false});
    //map.addLayer(judete_layer);

    var money_layer = new OpenLayers.Layer.MapServer(
        "money", App.MAPSERV_URL, {layers: 'money'},
        {gutter: 100,
         projection: App.webmerc,
         isBaseLayer: false});
    map.addLayer(money_layer);

};

$(document).ready(function() {
    App.init();
});

})();
