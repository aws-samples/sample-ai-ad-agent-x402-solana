/**
 * Configuration interface for the image generator
 */
export interface ImageGeneratorConfig {
    region?: string;
    modelId?: string;
    outputDir?: string;
}
/**
 * Parameters for image generation request
 */
export interface ImageGenerationParams {
    prompt: string;
    negativePrompt?: string;
    aspectRatio?: "16:9" | "1:1" | "21:9" | "2:3" | "3:2" | "4:5" | "5:4" | "9:16" | "9:21";
    outputFormat?: "jpeg" | "png";
    seed?: number;
}
/**
 * Image Generator class for AWS Bedrock Stability AI models
 */
export declare class BedrockImageGenerator {
    private client;
    private modelId;
    private outputDir;
    /**
     * Initialize the Bedrock Image Generator
     * @param config Configuration options
     */
    constructor(config?: ImageGeneratorConfig);
    /**
     * Ensure the output directory exists
     */
    private ensureOutputDirectory;
    /**
     * Generate images from a text prompt
     * @param params Image generation parameters
     * @returns Array of file paths to generated images
     */
    generateImages(params: ImageGenerationParams): Promise<string[]>;
    /**
     * Save base64 encoded images to files
     * @param images Array of base64 image strings
     * @param seeds Array of seeds used
     * @param prompt The prompt used (for filename generation)
     * @param format Output format
     * @returns Array of file paths
     */
    private saveImages;
    /**
     * Sanitize prompt text for use in filename
     * @param text Text to sanitize
     * @returns Sanitized filename-safe string
     */
    private sanitizeFilename;
    /**
     * Change the model being used
     * @param modelId New model ID
     */
    setModel(modelId: string): void;
    /**
     * Change the output directory
     * @param outputDir New output directory path
     */
    setOutputDir(outputDir: string): void;
}
/**
 * Convenience function to generate images with default settings
 * @param prompt Text prompt for image generation
 * @param config Optional configuration
 * @returns Array of file paths to generated images
 */
export declare function generateImage(prompt: string, config?: ImageGeneratorConfig): Promise<string[]>;
//# sourceMappingURL=imageGenerator.d.ts.map