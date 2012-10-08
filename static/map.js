(function() {

var App = window.App;

App.wgs84 = new OpenLayers.Projection("EPSG:4326");
App.webmerc = new OpenLayers.Projection("EPSG:900913");


App.map_point = function(lon, lat) {
    return new OpenLayers.LonLat(lon, lat).transform(App.wgs84, App.webmerc);
};


App.show_feature_info = function() {
    console.log('show_feature_info');
};


App.show_popup = function(options) {
    if(App.popup) {
        App.popup.destroy();
    }
    App.popup = new OpenLayers.Popup.FramedCloud(
        "the_popup",
        new OpenLayers.LonLat(options['x'], options['y']),
        null,
        options['content'],
        null,
        true
    );
    App.popup.closeOnMove = true;
    App.map.addPopup(App.popup);
};


App.map_clicked = function(e) {
    var map_lonlat = App.map.getLonLatFromPixel(e.xy)
    var coords = map_lonlat.clone().transform(App.webmerc, App.wgs84);
    var popup_content = "You clicked near " + coords.lat + " N, " +
                              + coords.lon + " E";
    App.show_popup({
        'content': popup_content,
        'x': map_lonlat.lon,
        'y': map_lonlat.lat
    });
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
        {gutter: 200,
         projection: App.webmerc,
         isBaseLayer: false});
    map.addLayer(money_layer);

    var click_control = new OpenLayers.Control;
    click_control.handler = new OpenLayers.Handler.Click(
        click_control,
        {'click': App.map_clicked},
        {'single': true,
         'double': false,
         'pixelTolerance': 0,
         'stopSingle': false,
         'stopDouble': false});
    App.map.addControl(click_control);
    click_control.activate();
};


$(document).ready(function() {
    App.init();
});

})();
