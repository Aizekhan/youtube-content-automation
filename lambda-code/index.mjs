import { DynamoDBClient } from "@aws-sdk/client-dynamodb";
import { DynamoDBDocumentClient, ScanCommand, QueryCommand, PutCommand } from "@aws-sdk/lib-dynamodb";

const client = new DynamoDBClient({ region: "eu-central-1" });
const docClient = DynamoDBDocumentClient.from(client);

export const handler = async (event) => {
  try {
    const { operation, params } = JSON.parse(event.body || "{}");
    
    let command;
    let result;
    
    switch (operation) {
      case "scan":
        command = new ScanCommand(params);
        result = await docClient.send(command);
        break;
        
      case "query":
        command = new QueryCommand(params);
        result = await docClient.send(command);
        break;
        
      case "put":
        command = new PutCommand(params);
        result = await docClient.send(command);
        break;
        
      default:
        throw new Error(`Unknown operation: ${operation}`);
    }
    
    return {
      statusCode: 200,
      headers: {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*"
      },
      body: JSON.stringify(result)
    };
    
  } catch (error) {
    return {
      statusCode: 500,
      headers: {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*"
      },
      body: JSON.stringify({ error: error.message })
    };
  }
};
