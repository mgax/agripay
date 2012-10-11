(function() {

var App = window.App;

App.wgs84 = new OpenLayers.Projection("EPSG:4326");
App.webmerc = new OpenLayers.Projection("EPSG:900913");


App.map_point = function(lon, lat) {
    return new OpenLayers.LonLat(lon, lat).transform(App.wgs84, App.webmerc);
};


App.show_feature_info = function(e) {
    var map_lonlat = App.map.getLonLatFromPixel(e.xy)
    App.hide_popup();
    if(! e.text) return;
    var popup_content = $(e.text);
    popup_content.find('li').each(function() {
        var li = $(this);
        var name = li.text();
        var href = '/table?localitate=' + encodeURIComponent(name);
        var link = $('<a>').text(name).attr({'href': href, 'target': '_blank'});
        li.empty().append(link);
    });
    App.show_popup({
        'content': $('<div>').append(popup_content).html(),
        'x': map_lonlat.lon,
        'y': map_lonlat.lat
    });
};


App.hide_popup = function() {
    if(App.popup) {
        App.popup.destroy();
        App.popup = null;
    }
};


App.show_popup = function(options) {
    App.hide_popup();
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

    //var money_layer = new OpenLayers.Layer.MapServer(
    //    "money", App.MAPSERV_URL, {layers: 'money'},
    //    {gutter: 200,
    //     projection: App.webmerc,
    //     isBaseLayer: false});
    var money_layer = new OpenLayers.Layer.WMS(
        "money", App.MAPSERV_URL, {layers: 'money', transparent: true},
        {gutter: 50,
         projection: App.webmerc,
         isBaseLayer: false});
    money_layer.srs = App.webmerc;
    map.addLayer(money_layer);

    var info_control = new OpenLayers.Control.WMSGetFeatureInfo({
        url: App.MAPSERV_URL,
        title: 'Identify features by clicking',
        layers: [money_layer],
        queryVisible: true
    });
    info_control.events.register("getfeatureinfo", App, App.show_feature_info);
    map.addControl(info_control);
    info_control.activate();
};


$(document).ready(function() {
    App.init();
});

})();
