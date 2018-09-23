$(document).ready(function(){
    // click on button submit

    $(document).on('click', '#action_button', function(){
        $.postJSON("/startnewgame", $("#form").serializeArray(), function(result) {

            console.log(result);
        }, "json");
    });

});
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
      console.error(xhr, resp, text)
    }
});
}