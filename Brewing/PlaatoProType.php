<?php
// Purpose: Get data from Plaato API
//  This script assumes it is configured with a "custom" parameter that defines the API key like:
//  {"apikey":"YOURPLAATOAPIKEY"}
use \TiqUtilities\Model\Node;
use \TiqUtilities\Model\Attribute;

require_once 'thinkiq_context.php';
$context = new Context();
$apikey = $context->custom_inputs->apikey;
if (!isset($apikey) || $apikey == "") {
    $msg = "No Plaato API key set, import script cannot run!";
    error_log($msg);
    print($msg);
    throw new Exception($msg);
}

// Find the target attributes to be updated
$parent = new Node($context->std_inputs->node_id);
$this_plaato = strtolower($parent->display_name);
echo "Updating: " . $this_plaato . "\r\n";
$parent->getAttributes();

$this_data = getParsedPlaatoData($this_plaato, $apikey);
if ($this_data == null) {
    echo("Could not find data from Plaato API that matches this device name!");
} else {
    echo "Found data for: " . $this_plaato . "\r\n";
    
    //Make time. TODO: Use device timestamp
    $the_time = $this_data->latestReading->time;
    echo "Device time: " . $the_time . "\r\n";
    $current_time_with_millisecond = DateTime::createFromFormat('U.u', microtime(true))->format(DateTimeInterface::RFC3339_EXTENDED);
    $times = [$current_time_with_millisecond];
    echo "Using Time: " . $times[0] . "\r\n";

    echo "\r\nActions:\r\n";
    $attribs = $parent->attributes;
    foreach($attribs as $attrib){
        $desc = $attrib->description;
        $values = [];
        if ($desc != "") {
            $descParts = explode("\\", $desc);
            $the_value = getProperty($this_data, $descParts);
            echo "- Need to update " . $attrib->relative_name . " of type: " . $attrib->data_type . ", from datasource: " . $desc;
            echo ", with value: " . $the_value . " \r\n";
            array_push($values, $the_value);
            if ($attrib->data_type == "float")
                $attrib->insertTimeSeries($values, $times);
            elseif ($attrib->data_type == "string") {
                $attrib->string_value = $values[0];
                $attrib->save();
            }
            elseif ($attrib->data_type == "bool") {
                if (isset($values[0]) && boolval($values[0]) == true) {
                    $attrib->string_value = boolval($values[0]);
                    $attrib->save();
                }
            }
        }
    }
    //echo json_encode($parent->attributes, JSON_PRETTY_PRINT) . "\r\n";
}
echo "\r\nCompleted update at " . $times[0];

function getProperty($obj, $property) {
  foreach( $property as $p ) {
     $obj = $obj->{$p};
   }
   return $obj;
}

function getParsedPlaatoData($this_plaato, $apikey) {
    $response = getPlaatoData($apikey);
    $jsonArray = json_decode($response);
    foreach($jsonArray as $value){
        $curr_plaato = strtolower($value->name);
        if ($this_plaato == $curr_plaato)
            return $value;
    }
}

function getPlaatoData($apikey) {
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_URL, 'https://api.plaato.cloud/devices');
    curl_setopt($ch, CURLOPT_HTTPHEADER, [
        'x-plaato-api-key: ' . $apikey
    ]);
    $response = curl_exec($ch);
    if(curl_error($ch)) {
        fwrite($fp, curl_error($ch));
    }
    curl_close($ch);
    return $response;
}
?>