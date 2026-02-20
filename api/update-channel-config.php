<?php
header('Content-Type: application/json; charset=utf-8');
require_once __DIR__ . '/../oauth/vendor/autoload.php';
use Aws\DynamoDb\DynamoDbClient;

$channelId = $_POST['channel_id'] ?? '';
if (!$channelId) {
    http_response_code(400);
    echo json_encode(['success' => false, 'error' => 'channel_id required']);
    exit;
}

$dynamodb = new DynamoDbClient(['version' => 'latest', 'region' => 'eu-central-1']);

// DynamoDB reserved keywords - РОЗШИРЕНИЙ СПИСОК
$reservedKeywords = [
    'format', 'name', 'date', 'timestamp', 'value', 'type', 'status',
    'order', 'group', 'table', 'user', 'data', 'key', 'index',
    'timezone', 'time', 'zone', 'range', 'size', 'attributes',
    'language', 'description', 'role', 'comment', 'connection',
    'mode'  // Added for Story Engine fields (story_mode, character_mode, etc.)
];

$updateExpression = 'SET updated_at = :now';
$expressionValues = [':now' => ['S' => date('c')]];
$expressionNames = [];

foreach ($_POST as $key => $value) {
    if ($key !== 'channel_id' && $value !== '') {
        $placeholder = ":$key";
        
        // Перевірка на reserved keywords
        if (in_array(strtolower($key), $reservedKeywords)) {
            $namePlaceholder = "#$key";
            $expressionNames[$namePlaceholder] = $key;
            $updateExpression .= ", $namePlaceholder = $placeholder";
        } else {
            $updateExpression .= ", $key = $placeholder";
        }
        
        $expressionValues[$placeholder] = ['S' => $value];
    }
}

try {
    $result = $dynamodb->scan([
        'TableName' => 'ChannelConfigs',
        'FilterExpression' => 'channel_id = :cid',
        'ExpressionAttributeValues' => [':cid' => ['S' => $channelId]]
    ]);

    if (empty($result['Items'])) {
        echo json_encode(['success' => false, 'error' => 'Config not found']);
        exit;
    }

    $configId = $result['Items'][0]['config_id']['S'];
    
    $updateParams = [
        'TableName' => 'ChannelConfigs',
        'Key' => ['config_id' => ['S' => $configId]],
        'UpdateExpression' => $updateExpression,
        'ExpressionAttributeValues' => $expressionValues
    ];
    
    if (!empty($expressionNames)) {
        $updateParams['ExpressionAttributeNames'] = $expressionNames;
    }
    
    $dynamodb->updateItem($updateParams);

    echo json_encode(['success' => true, 'message' => 'Config updated', 'channel_id' => $channelId]);
} catch (Exception $e) {
    http_response_code(500);
    echo json_encode(['success' => false, 'error' => $e->getMessage()]);
}
?>
