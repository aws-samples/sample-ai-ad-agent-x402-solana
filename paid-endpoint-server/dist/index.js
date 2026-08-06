"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const dotenv_1 = require("dotenv");
const express_1 = __importDefault(require("express"));
const x402_express_1 = require("x402-express");
const axios_1 = __importDefault(require("axios"));
const imageGenerator_1 = require("./imageGenerator");
const path_1 = __importDefault(require("path"));
// Load environment variables
(0, dotenv_1.config)();
// Get configuration from environment
const SELLER_ADDRESS = process.env.SELLER_ADDRESS;
const FACILITATOR_URL = process.env.FACILITATOR_URL;
const OPENWEATHER_API_KEY = process.env.OPENWEATHER_API_KEY;
const PAYMENT_TOKEN_ID = process.env.PAYMENT_TOKEN_ID;
const AWS_REGION = process.env.AWS_REGION || "us-west-2";
const HOST = process.env.HOST || "127.0.0.1";
const PORT = parseInt(process.env.PORT || "4021", 10);
if (!SELLER_ADDRESS) {
    throw new Error("Missing required environment variable: SELLER_ADDRESS");
}
if (!FACILITATOR_URL) {
    throw new Error("Missing required environment variable: FACILITATOR_URL");
}
if (!OPENWEATHER_API_KEY) {
    throw new Error("Missing required environment variable: OPENWEATHER_API_KEY");
}
// Initialize Bedrock Image Generator
const imageGenerator = new imageGenerator_1.BedrockImageGenerator({
    region: AWS_REGION,
    modelId: "stability.stable-image-core-v1:1", // "stability.stable-image-ultra-v1:0",
    outputDir: path_1.default.join(__dirname, "../../output"),
});
// Updated validation function
function validateQuery(query) {
    if (!query) {
        throw new Error("Query is required");
    }
    // Handle array of queries
    if (Array.isArray(query)) {
        if (query.length === 0) {
            throw new Error("Query array cannot be empty");
        }
        if (query.length > 10) {
            throw new Error("Query array must contain 10 or fewer items");
        }
        return query.map((q, index) => {
            if (typeof q !== "string") {
                throw new Error(`Query at index ${index} must be a string`);
            }
            const trimmed = q.trim();
            if (trimmed.length === 0) {
                throw new Error(`Query at index ${index} cannot be empty or whitespace only`);
            }
            if (trimmed.length > 1000) {
                throw new Error(`Query at index ${index} must be less than 1000 characters`);
            }
            return trimmed;
        });
    }
    // Handle single string query
    if (typeof query !== "string") {
        throw new Error("Query must be a string or array of strings");
    }
    const trimmedQuery = query.trim();
    if (trimmedQuery.length === 0) {
        throw new Error("Query cannot be empty or whitespace only");
    }
    if (trimmedQuery.length > 1000) {
        throw new Error("Query must be less than 1000 characters");
    }
    return trimmedQuery;
}
function validateCity(city) {
    if (!city || typeof city !== "string") {
        throw new Error("City is required and must be a string");
    }
    const trimmedCity = city.trim();
    if (trimmedCity.length === 0) {
        throw new Error("City cannot be empty or whitespace only");
    }
    if (trimmedCity.length > 100) {
        throw new Error("City name must be less than 100 characters");
    }
    return trimmedCity;
}
function validateUnits(units) {
    if (!units) {
        return "metric";
    }
    if (!["metric", "imperial", "standard"].includes(units)) {
        throw new Error("Units must be metric, imperial, or standard");
    }
    return units;
}
// Updated image generation function
async function createImagesWithAgent(query) {
    try {
        const allFilePaths = [];
        // Handle array of queries
        if (Array.isArray(query)) {
            console.log(`Generating images for ${query.length} different prompts`);
            for (let i = 0; i < query.length; i++) {
                const prompt = query[i];
                console.log(`Processing prompt ${i + 1}/${query.length}: "${prompt}"`);
                const filePaths = await imageGenerator.generateImages({
                    prompt: prompt,
                });
                allFilePaths.push(...filePaths);
                console.log(`Generated ${filePaths.length} image(s) for prompt ${i + 1}`);
            }
            const message = `${allFilePaths.length} image(s) generated successfully from ${query.length} prompt(s)! Saved at:\n${allFilePaths.join(",\n")}`;
            return {
                message,
                paths: allFilePaths,
            };
        }
        // Handle single string query (existing logic)
        const numImagesMatch = query.match(/(\d+)\s+images?/i);
        let numImages = numImagesMatch ? parseInt(numImagesMatch[1]) : 1;
        numImages = Math.min(Math.max(numImages, 1), 10); // Limit between 1-10
        // Clean up the prompt by removing the number specification
        let prompt = query.replace(/generate\s+(\d+\s+)?images?\s+(of|showing)?\s*/i, "").trim();
        if (prompt.length === 0) {
            prompt = query;
        }
        console.log(`Generating ${numImages} image(s) with prompt: "${prompt}"`);
        // Generate images sequentially
        for (let i = 0; i < numImages; i++) {
            console.log(`Generating image ${i + 1}/${numImages}...`);
            const filePaths = await imageGenerator.generateImages({
                prompt: prompt,
            });
            allFilePaths.push(...filePaths);
        }
        const message = `${allFilePaths.length} image(s) generated successfully! Saved at:\n${allFilePaths.join(",\n")}`;
        return {
            message,
            paths: allFilePaths,
        };
    }
    catch (error) {
        console.error("Error generating images:", error);
        if (error instanceof Error) {
            throw new Error(`Image generation failed: ${error.message}`);
        }
        throw new Error("Image generation failed with unknown error");
    }
}
// Weather data fetching function
async function getWeatherData(city, units = "metric") {
    const baseUrl = "https://api.openweathermap.org/data/2.5/weather";
    try {
        const response = await axios_1.default.get(baseUrl, {
            params: {
                q: city,
                appid: OPENWEATHER_API_KEY,
                units: units,
            },
            timeout: 30000,
        });
        return response.data;
    }
    catch (error) {
        if (axios_1.default.isAxiosError(error)) {
            if (error.code === "ECONNABORTED") {
                throw new Error(`Timeout error fetching weather data for ${city}`);
            }
            throw new Error(`Error fetching weather data: ${error.response?.data?.message || error.message}`);
        }
        throw error;
    }
}
// Initialize Express app
const app = (0, express_1.default)();
// Body parser middleware
app.use(express_1.default.json());
// Serve static files from generated_images directory
app.use('/images', express_1.default.static(path_1.default.join(__dirname, '../../output')));
// Apply payment middleware with facilitator configuration
app.use((0, x402_express_1.paymentMiddleware)(SELLER_ADDRESS, {
    "POST /image_generator": {
        price: {
            amount: "100000", // 100 USDC (6 decimals) 4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU
            asset: {
                address: PAYMENT_TOKEN_ID,
                decimals: 6,
            },
        },
        network: "solana-devnet",
        description: "Image generation service using AWS Bedrock Stable Diffusion",
        inputSchema: {
            bodyType: "json",
            bodyFields: {
                query: {
                    type: ["string", "array"], // Accept both types
                    description: "The prompt(s) for image generation. Can be a single string (e.g., 'Generate image of a sunset') or an array of strings for different prompts (e.g., ['sunset over mountains', 'city at night'])",
                    required: true,
                    // For array validation
                    minItems: 1,
                    maxItems: 4,
                    // For string validation
                    minLength: 1,
                    maxLength: 1000,
                },
            },
        },
        outputSchema: {
            type: "object",
            properties: {
                success: {
                    type: "boolean",
                    description: "Whether the image generation was successful",
                },
                content: {
                    type: "string",
                    description: "Message with information about generated images",
                },
                imagePaths: {
                    type: "array",
                    items: {
                        type: "string",
                    },
                    description: "Array of file paths to generated images",
                },
                error: {
                    type: "string",
                    description: "Error message if success is false",
                },
            },
        },
    },
    "POST /weather": {
        // price: "$0.0001",
        price: {
            amount: "100000", // 100 USDC (6 decimals) 4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU
            asset: {
                address: PAYMENT_TOKEN_ID,
                decimals: 6,
            },
        },
        network: "solana-devnet",
        description: "Weather information service",
        inputSchema: {
            bodyType: "json",
            bodyFields: {
                city: {
                    type: "string",
                    description: "City name (e.g., 'London' or 'London,UK')",
                    required: true,
                    minLength: 1,
                    maxLength: 100,
                },
                units: {
                    type: "string",
                    description: "Units of measurement: 'metric', 'imperial', or 'standard'",
                    enum: ["metric", "imperial", "standard"],
                    required: false,
                },
            },
        },
        outputSchema: {
            type: "object",
            properties: {
                temperature: { type: "number" },
                feels_like: { type: "number" },
                temp_min: { type: "number" },
                temp_max: { type: "number" },
                pressure: { type: "number" },
                humidity: { type: "number" },
                description: { type: "string" },
                wind_speed: { type: "number" },
                clouds: { type: "number" },
                city: { type: "string" },
                country: { type: "string" },
            },
        },
    },
}, {
    // Facilitator configuration - THIS WAS MISSING!
    url: FACILITATOR_URL,
}));
// Root endpoint
app.get("/", (req, res) => {
    res.json({
        message: "Payment-Gated API",
        endpoints: {
            image_generator: "POST /image_generator - 100 USDC on Solana - Generate images with AWS Bedrock",
            weather: "POST /weather - 0.001 USDC on Solana - Get weather information",
        },
        info: {
            network: "Solana Devnet",
            paymentAddress: SELLER_ADDRESS,
            facilitator: FACILITATOR_URL,
            imageModel: "Stable Diffusion Models via AWS Bedrock",
        },
    });
});
// Image generation endpoint
app.post("/image_generator", async (req, res) => {
    try {
        const { query } = req.body;
        const validatedQuery = validateQuery(query);
        console.log(`Image generation request: "${validatedQuery}"`);
        const result = await createImagesWithAgent(validatedQuery);
        res.json({
            success: true,
            content: result.message,
            imagePaths: result.paths,
        });
    }
    catch (error) {
        console.error("Error in image generation:", error);
        res.json({
            success: false,
            error: error instanceof Error ? error.message : "Unknown error occurred",
        });
    }
});
// Weather endpoint
app.post("/weather", async (req, res) => {
    try {
        const { city, units } = req.body;
        const validatedCity = validateCity(city);
        const validatedUnits = validateUnits(units);
        console.log(`Weather request for city: ${validatedCity}, units: ${validatedUnits}`);
        const weatherData = await getWeatherData(validatedCity, validatedUnits);
        const weatherResponse = {
            temperature: weatherData.main.temp,
            feels_like: weatherData.main.feels_like,
            temp_min: weatherData.main.temp_min,
            temp_max: weatherData.main.temp_max,
            pressure: weatherData.main.pressure,
            humidity: weatherData.main.humidity,
            description: weatherData.weather[0].description,
            wind_speed: weatherData.wind.speed,
            clouds: weatherData.clouds.all,
            city: weatherData.name,
            country: weatherData.sys.country,
        };
        console.log(`Weather data retrieved successfully for ${validatedCity}`);
        res.json(weatherResponse);
    }
    catch (error) {
        console.error("Error in weather endpoint:", error);
        res.json({
            error: error instanceof Error ? error.message : "Unknown error occurred",
        });
    }
});
// Start server
app.listen(PORT, HOST, () => {
    console.log(`Server listening at https://${HOST}:${PORT}`);
    console.log(`Network: Solana Devnet`);
    console.log(`Payment address: ${SELLER_ADDRESS}`);
    console.log(`Facilitator: ${FACILITATOR_URL}`);
    console.log(`Image model: Stable Diffusion (AWS Bedrock)`);
    // console.log(`Generated images will be accessible at: https://${HOST}:${PORT}/images/`);
});
//# sourceMappingURL=index.js.map