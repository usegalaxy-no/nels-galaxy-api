<?php

     if (!isset($_GET["action"])) errorPage("Missing 'action' GET parameter");
else if (!($_GET["action"]=="import" || $_GET["action"]=="export")) errorPage("Wrong 'action' parameter. Expected 'import' or 'export' but got '".$action."'");     
else if (!isset($_POST["selectedFiles"])) errorPage("Missing 'selectedFiles' POST parameter");
else {

   $action=$_GET["action"];
   $url=url_origin($_SERVER);
   $parts=explode("/static/", $url);
   $galaxy_root=$parts[0]; // the root URL of this Galaxy server
   $api_url=$galaxy_root."/api/webhooks/nels_".$action."_history/data"; // URL to webhook API
   $cookies="";
   foreach ($_COOKIE as $key => $value) {$cookies.=$key."=".$value.";";} // convert $_COOKIE array to string
   $response = callAPI($api_url,$cookies); // GET information about the user and history from Galaxy via the webhook API. Authentication is taken care of by the cookie
   // I should probably check for errors here...
   $fields = array();
   $fields['action']=$action;
   $fields['user']=$response['username']; // I am using this for now, but not sure if this will be the final choice
   $fields['userid']=$response['userid'];
   $fields['username']=$response['username'];
   $fields['email']=$response['email'];
   $fields['galaxy']=$galaxy_root;

   if ($action=="import") {
       $selectedFile=$_POST['selectedFiles'];
       $parts=explode(",", $selectedFile); // selectedFiles is a comma-separated list of file paths from the NeLS Storage
       $selectedFile=$parts[0];  // just import the first of the selected files (for now...)
       $parts=explode("/", $selectedFile);       
       $fields['historyname']=end($parts); // discard the path prefixes to get only the file name. This is just used for reporting progress back to the user.
       $fields['historyfile']=$selectedFile; // this is the full file path
   } else {
       $fields['history']=$response['history']; // encrypted history ID
       $fields['historyname']=$response['historyname']; // name of history in Galaxy. This is just used for reporting progress back to the user.
       $fields['nels_directory']=$_POST['selectedFiles']; // Directory to export history file to. selectedFiles should here be the path to a single folder from the NeLS Storage
   }

   // make POST call to NeLS API to initiate the transfer of the history
   $nels_api_url="https://tare.medisin.ntnu.no/nels_portal/api.php"; // this refers to my mock portal
   $response = postAPI($nels_api_url,$fields);

   // I should probably check the response to see if anything went wrong.
   // errorPage(json_encode($response)); // just output the response as JSON

   // Finally, redirect back to Galaxy so we can start tracking the progress via the welcome page
   header("Location: ".$galaxy_root); // this also sets the HTTP status code to "302 FOUND" (redirection)

}


// -------------------------------------------------

/* Return HTML error page instead of JSON. This is just for temporary debugging. Errors should probably be handled better than this */
function errorPage($message) {
  header('Content-Type: text/html');  
  echo "<html><body>";
  echo "<h2>Error:".$message."</h2>";
  echo "</body></html>";
  exit;
}

/* Get the full URL of the server */
function url_origin( $s, $use_forwarded_host = false )
{   
    $ssl      = ( ! empty( $s['HTTPS'] ) && $s['HTTPS'] == 'on' );
    $sp       = strtolower( $s['SERVER_PROTOCOL'] );
    $protocol = substr( $sp, 0, strpos( $sp, '/' ) ) . ( ( $ssl ) ? 's' : '' );
    $port     = $s['SERVER_PORT'];
    $port     = ( ( ! $ssl && $port=='80' ) || ( $ssl && $port=='443' ) ) ? '' : ':'.$port;
    $host     = ( $use_forwarded_host && isset( $s['HTTP_X_FORWARDED_HOST'] ) ) ? $s['HTTP_X_FORWARDED_HOST'] : ( isset( $s['HTTP_HOST'] ) ? $s['HTTP_HOST'] : null );
    $host     = isset( $host ) ? $host : $s['SERVER_NAME'] . $port;
    return $protocol . '://' . $host.$s['REQUEST_URI'];;
}

/* Make a GET request to a REST API that returns JSON, parse the result and return it as an associative array */
function callAPI($url, $cookie=null) {
     $ch = curl_init();
     curl_setopt($ch, CURLOPT_URL, $url);
     curl_setopt($ch, CURLOPT_RETURNTRANSFER, TRUE);
     if ($cookie) curl_setopt($ch, CURLOPT_HTTPHEADER, array("Cookie: ".$cookie));
     $response = curl_exec($ch);
     if ($response === false) {
        $error='"'.curl_error($ch).'" - Code: '.curl_errno($ch);
        curl_close($ch);
	errorPage($error);
     } else {
        curl_close($ch);
        $data=json_decode($response, TRUE);
        if (is_null($data)) errorPage("ERROR: Unable to decode expected JSON return value from NeLS API");
        if (!is_array($data)) errorPage("ERROR: return value from NeLS API is not an array");
        return $data;
     }
}

/* Make a POST request to a REST API that returns JSON, parse the result and return it as an associative array */
function postAPI($url,$fields,$cookie=null) { // $fields is an associative array 
     $fields_string = http_build_query($fields);
     $ch = curl_init();
     curl_setopt($ch, CURLOPT_URL, $url);
     curl_setopt($ch, CURLOPT_POST, true);
     curl_setopt($ch, CURLOPT_POSTFIELDS, $fields_string);     
     curl_setopt($ch, CURLOPT_RETURNTRANSFER, TRUE);
     if ($cookie) curl_setopt($ch, CURLOPT_HTTPHEADER, array("Cookie: ".$cookie));
     $response = curl_exec($ch);
     if ($response === false) {
        $error='"'.curl_error($ch).'" - Code: '.curl_errno($ch);
        curl_close($ch);
        errorPage($error);
     } else {
        curl_close($ch);
        $data=json_decode($response, TRUE);
        if (is_null($data)) errorPage("ERROR: Unable to decode expected JSON return value from NeLS API");
        if (!is_array($data)) errorPage("ERROR: return value from NeLS API is not an array");
        return $data;
     }
}


?>
