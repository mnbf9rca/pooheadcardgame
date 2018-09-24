$(document).ready(function(){
    // click on button submit

    $(document).on('click', '#action_button', function(){
        $.postJSON("/startnewgame", $("#form").serializeArray(), function(result) {

            process_response(result);
        }, "json");
    });

});

function process_response(response_json){
    console.log(response_json)
    if (response_json["startnewgame"] == false){
        display_alert(response_json["message"])
    } else {
        document.location.replace(response_json["redirect"])
    }

}

function display_alert(alert_message, alert_class = "alert-primary"){
    $("#alert-pane").remove()
    let div = document.createElement("div");
    div.setAttribute("id","alert-pane")
    div.className = "alert " + alert_class
    let newContent = document.createTextNode(alert_message);
    div.appendChild(newContent)
    $('#alert-placeholder').append(div)
}

$.postJSON = function(url, data, success, dataType) {
// modified from https://gist.github.com/padcom/1557142/7ebb6a9c632f02ecb10a57e18340c5eae86b251e

if (typeof data != 'string') {
    data = JSON.stringify(data);
}
$.ajax({
    url : url,
    type: "post",
    data: data,
    dataType: dataType || "json",
    contentType: "application/json",
    success: success,
    error: function(xhr, status, error) {
      console.error(xhr, status, error)
    }
});
}