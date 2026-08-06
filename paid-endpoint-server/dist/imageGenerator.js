"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.BedrockImageGenerator = void 0;
exports.generateImage = generateImage;
const client_bedrock_runtime_1 = require("@aws-sdk/client-bedrock-runtime");
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
/**
 * Image Generator class for AWS Bedrock Stability AI models
 */
class BedrockImageGenerator {
    client;
    modelId;
    outputDir;
    /**
     * Initialize the Bedrock Image Generator
     * @param config Configuration options
     */
    constructor(config = {}) {
        const region = config.region || process.env.AWS_REGION || "us-west-2";
        // Use the latest version :1 not :0
        this.modelId =
            config.modelId || "stability.stable-image-ultra-v1:1";
        this.outputDir = config.outputDir || "../../output";
        this.client = new client_bedrock_runtime_1.BedrockRuntimeClient({
            region,
        });
        // Ensure output directory exists
        this.ensureOutputDirectory();
    }
    /**
     * Ensure the output directory exists
     */
    ensureOutputDirectory() {
        if (!fs.existsSync(this.outputDir)) {
            fs.mkdirSync(this.outputDir, { recursive: true });
            console.log(`Created output directory: ${this.outputDir}`);
        }
    }
    /**
     * Generate images from a text prompt
     * @param params Image generation parameters
     * @returns Array of file paths to generated images
     */
    async generateImages(params) {
        try {
            console.log(`Generating images with prompt: "${params.prompt}"`);
            console.log(`Using model: ${this.modelId}`);
            // Prepare the request body for Stability AI Image Services
            const requestBody = {
                prompt: params.prompt,
                mode: "text-to-image",
            };
            // Add optional parameters
            if (params.negativePrompt) {
                requestBody.negative_prompt = params.negativePrompt;
            }
            if (params.aspectRatio) {
                requestBody.aspect_ratio = params.aspectRatio;
            }
            if (params.seed !== undefined) {
                requestBody.seed = params.seed;
            }
            if (params.outputFormat) {
                requestBody.output_format = params.outputFormat;
            }
            console.log("Request body:", JSON.stringify(requestBody, null, 2));
            // Prepare the invoke model command
            const invokeParams = {
                modelId: this.modelId,
                contentType: "application/json",
                accept: "application/json",
                body: JSON.stringify(requestBody),
            };
            // Invoke the model
            const command = new client_bedrock_runtime_1.InvokeModelCommand(invokeParams);
            const response = await this.client.send(command);
            if (!response.body) {
                throw new Error("No response body received from Bedrock");
            }
            // Decode and parse the response
            const jsonString = new TextDecoder().decode(response.body);
            const modelResponse = JSON.parse(jsonString);
            console.log(`Successfully generated ${modelResponse.images.length} image(s)`);
            // Save images and return file paths
            const filePaths = await this.saveImages(modelResponse.images, modelResponse.seeds || [], params.prompt, params.outputFormat || "png");
            return filePaths;
        }
        catch (error) {
            console.error("Error generating images:", error);
            throw error;
        }
    }
    /**
     * Save base64 encoded images to files
     * @param images Array of base64 image strings
     * @param seeds Array of seeds used
     * @param prompt The prompt used (for filename generation)
     * @param format Output format
     * @returns Array of file paths
     */
    async saveImages(images, seeds, prompt, format) {
        const filePaths = [];
        const timestamp = Date.now();
        const sanitizedPrompt = this.sanitizeFilename(prompt);
        const extension = format === "jpeg" ? "jpg" : format;
        for (let i = 0; i < images.length; i++) {
            const base64Image = images[i];
            const seed = seeds[i] !== undefined ? seeds[i] : 0;
            // Decode base64 image
            const imageBuffer = Buffer.from(base64Image, "base64");
            // Generate filename
            // const filename = `${sanitizedPrompt}_${timestamp}_${i + 1}_seed${seed}.${extension}`;
            const filename = `${sanitizedPrompt}_${timestamp}.${extension}`;
            const filePath = path.join(this.outputDir, filename);
            // Write image to file
            fs.writeFileSync(filePath, imageBuffer);
            console.log(`Saved image: ${filePath}`);
            filePaths.push(filePath);
        }
        return filePaths;
    }
    /**
     * Sanitize prompt text for use in filename
     * @param text Text to sanitize
     * @returns Sanitized filename-safe string
     */
    sanitizeFilename(text) {
        return text
            .toLowerCase()
            .replace(/[^a-z0-9]+/g, "_")
            .replace(/^_+|_+$/g, "")
            .substring(0, 50); // Limit length
    }
    /**
     * Change the model being used
     * @param modelId New model ID
     */
    setModel(modelId) {
        this.modelId = modelId;
        console.log(`Model changed to: ${modelId}`);
    }
    /**
     * Change the output directory
     * @param outputDir New output directory path
     */
    setOutputDir(outputDir) {
        this.outputDir = outputDir;
        this.ensureOutputDirectory();
    }
}
exports.BedrockImageGenerator = BedrockImageGenerator;
/**
 * Convenience function to generate images with default settings
 * @param prompt Text prompt for image generation
 * @param config Optional configuration
 * @returns Array of file paths to generated images
 */
async function generateImage(prompt, config) {
    const generator = new BedrockImageGenerator(config);
    return generator.generateImages({ prompt });
}
//# sourceMappingURL=imageGenerator.js.map