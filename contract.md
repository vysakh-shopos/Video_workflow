# Version 2 API Contracts

Complete API contract documentation for the Video Copilot v2 API endpoints.

---

## Table of Contents

1. [Creative Analysis](#1-creative-analysis)
2. [Image Generation](#2-image-generation)
3. [Clip Generation](#3-clip-generation)
4. [Auto Stitch](#4-auto-stitch)
5. [Manual Stitch](#5-manual-stitch)
6. [Edit](#6-edit)
7. [Regenerate](#7-regenerate)
8. [Prompt Adaptation](#8-prompt-adaptation)
9. [Fetch Template](#9-fetch-template)

---

## 1. Creative Analysis

**Endpoint:** `POST /v2/creative-analysis`

**Description:** Analyze garment and moodboard/exemplars to generate structured prompts using GPT-4 vision.

### Request Schema

```json
{
  "garment_image": "string (required) - URL or path to garment image",
  "moodboard_image": "string (optional) - URL or path to moodboard image",
  "user_request": "string (optional) - Creative direction/request",
  "brand_memory": "object (optional) - Brand guidelines and memory as JSON",
  "prompt_type": "string (default: 'studio') - 'studio' or 'lifestyle'",
  "num_prompts": "integer (default: 4, min: 1, max: 20) - Number of prompts to generate"
}
```

### Response Schema

```json
{
  "success": "boolean",
  "message": "string",
  "garment_analysis": "string - Detailed analysis of the garment",
  "moodboard_analysis": "string (optional) - Analysis of moodboard patterns",
  "concepts": [
    {
      "concept_name": "string",
      "concept_description": "string",
      "scenes": [
        {
          "scene": "string",
          "model": {
            "origin": "string",
            "ethnicity": "string",
            "gender": "string",
            "bodyType": "string",
            "height": "string",
            "age": "string",
            "skinTone": "string",
            "appearance": "string",
            "hair": {
              "color": "string",
              "style": "string"
            }
          },
          "pose": "string",
          "styling": {
            "outfit": "string",
            "shoes": "string",
            "other_garment": "string (optional)",
            "accessories": "string (optional)"
          },
          "photography": {
            "camera": "string",
            "cameraAngle": "string",
            "resolution": "string",
            "lighting": "string",
            "background": "string"
          },
          "quality": "string",
          "mood": "string"
        }
      ]
    }
  ],
  "structured_prompts": "array - Flattened list of all scenes (backward compatibility)",
  "num_prompts": "integer - Total number of scenes generated"
}
```

### Example Request

```bash
curl -X POST "http://localhost:8000/v2/creative-analysis" \
  -H "Content-Type: application/json" \
  -d '{
    "garment_image": "https://example.com/garment.jpg",
    "prompt_type": "studio",
    "num_prompts": 4
  }'
```

---

## 2. Image Generation

**Endpoint:** `POST /v2/image-generation`

**Description:** Generate images from structured prompts using Replicate's Flux model with garment reference.

### Request Schema

```json
{
  "prompts": [
    {
      "scene": "string",
      "model": "object - Model characteristics",
      "pose": "string",
      "styling": "object - Styling details",
      "photography": "object - Photography setup",
      "quality": "string",
      "mood": "string"
    }
  ],
  "garment_image": "string (required) - URL or path to garment reference image",
  "num_images": "integer (optional) - Number of images to generate (defaults to len(prompts))"
}
```

### Response Schema

```json
{
  "success": "boolean",
  "images": [
    {
      "success": "boolean",
      "prompt_index": "integer",
      "image_url": "string - S3 URL or local path",
      "image_path": "string - Local file path",
      "error": "string (optional)",
      "structured_prompt": "object - The prompt used"
    }
  ]
}
```

### Notes

- First image is generated independently
- Remaining images are generated concurrently using the first image as reference for consistency
- Automatic retry logic (up to 3 attempts per image)
- Images uploaded to S3: `generated/images/{request_id}/image_{index}.jpg`

### Example Request

```bash
curl -X POST "http://localhost:8000/v2/image-generation" \
  -H "Content-Type: application/json" \
  -d '{
    "garment_image": "https://example.com/garment.jpg",
    "prompts": [
      {
        "scene": "Modern studio with white background",
        "model": {...},
        "pose": "Standing confidently",
        "styling": {...},
        "photography": {...},
        "quality": "Ultra HD, photorealistic",
        "mood": "Professional and clean"
      }
    ],
    "num_images": 1
  }'
```

---

## 3. Clip Generation

**Endpoint:** `POST /v2/clip-generation`

**Description:** Generate video clips from images using Kling AI video generation model.

### Request Schema

```json
{
  "scene_prompts": [
    "string - Text scene prompt for video generation"
  ],
  "image": "string (required) - URL or path to source image",
  "video_model": "string (default: 'kling') - Video generation model",
  "video_settings": "object (optional) - Video generation settings"
}
```

### Response Schema

```json
{
  "success": "boolean",
  "videos": [
    {
      "success": "boolean",
      "scene_prompt": "string",
      "video_url": "string - S3 URL or local path",
      "video_path": "string - Local file path",
      "error": "string (optional)",
      "prompt_used": "string - Final prompt used for generation"
    }
  ]
}
```

### Notes

- All clips generated concurrently
- Currently only supports 'kling' model
- Videos uploaded to S3: `videos/{request_id}/clip_{index}.mp4`

### Example Request

```bash
curl -X POST "http://localhost:8000/v2/clip-generation" \
  -H "Content-Type: application/json" \
  -d '{
    "image": "https://example.com/image.jpg",
    "scene_prompts": [
      "Model walking confidently in modern studio",
      "Close-up of fabric texture and details"
    ],
    "video_model": "kling"
  }'
```

---

## 4. Auto Stitch

**Endpoint:** `POST /v2/auto-stitch`

**Description:** Automatically stitch videos with AI-driven editing using Gemini AI for intelligent scene analysis and beat-synchronized editing.

### Request Schema

```json
{
  "videos": [
    "string - Video URL or path (minimum 2 videos required)"
  ],
  "music": "string (optional) - Music file URL or path",
  "creative_prompt": "string (optional) - Creative direction for AI editing",
  "beat_sync": "boolean (optional) - Enable beat-synchronized editing (defaults to true if music provided)"
}
```

### Response Schema

```json
{
  "success": "boolean",
  "message": "string",
  "final_video": "string - S3 URL or local path to final video",
  "method": "string - Editing method used (e.g., 'ai_video_editor')",
  "ai_driven": "boolean - Whether AI-driven editing was used",
  "beat_sync": "boolean - Whether beat synchronization was applied",
  "segments": "integer - Number of segments used",
  "crew_result": "string - AI editing plan/details"
}
```

### Notes

- Requires at least 2 videos
- Supports S3 URLs (format: `s3://bucket/prefix`)
- AI analyzes scenes and creates intelligent cuts
- Beat synchronization requires music file
- Final video uploaded to S3: `final-videos/{request_id}/ai_final.mp4`

### Example Request

```bash
curl -X POST "http://localhost:8000/v2/auto-stitch" \
  -H "Content-Type: application/json" \
  -d '{
    "videos": [
      "https://example.com/clip1.mp4",
      "https://example.com/clip2.mp4",
      "https://example.com/clip3.mp4"
    ],
    "music": "https://example.com/music.mp3",
    "creative_prompt": "Create a dynamic fashion showcase with smooth transitions",
    "beat_sync": true
  }'
```

---

## 5. Manual Stitch

**Endpoint:** `POST /v2/manual-stitch`

**Description:** Manually stitch videos using template metadata with precise control over durations, transitions, and effects.

### Request Schema

```json
{
  "videos": [
    "string - Video URL or path"
  ],
  "template_metadata": {
    "clip_durations": [
      "float - Duration for each clip in seconds"
    ],
    "transition_types": [
      "string (optional) - Transition type ('cut', 'crossfade', etc.)"
    ],
    "transition_durations": [
      "float (optional) - Duration of each transition in seconds"
    ],
    "logo_outro": "boolean (default: false) - Add logo outro",
    "music_file": "string (optional) - Background music URL or path",
    "logo_file": "string (optional) - Logo image URL or path"
  }
}
```

### Response Schema

```json
{
  "success": "boolean",
  "message": "string",
  "final_video": "string - S3 URL or local path to final video",
  "template_applied": "string - Name of template applied",
  "num_clips": "integer - Number of clips stitched",
  "total_duration": "float - Total duration in seconds"
}
```

### Notes

- Number of videos must match number of clip durations
- Supports S3 URLs (format: `s3://bucket/prefix`)
- Final video uploaded to S3: `final-videos/{request_id}/manual_stitched.mp4`

### Example Request

```bash
curl -X POST "http://localhost:8000/v2/manual-stitch" \
  -H "Content-Type: application/json" \
  -d '{
    "videos": [
      "https://example.com/clip1.mp4",
      "https://example.com/clip2.mp4"
    ],
    "template_metadata": {
      "clip_durations": [3.0, 4.0],
      "transition_types": ["crossfade"],
      "transition_durations": [0.5],
      "logo_outro": true,
      "music_file": "https://example.com/music.mp3"
    }
  }'
```

---

## 6. Edit

**Endpoint:** `POST /v2/edit`

**Description:** Edit images or videos based on user text instructions using AI-powered editing models.

### Request Schema

```json
{
  "urls": [
    "string - URL of file to edit (minimum 1 required)"
  ],
  "user_text": "string (required, min_length: 1) - User's text instruction for editing",
  "data_type": "string (required) - Type of data: 'image' or 'video'",
  "chat_id": "string (required, min_length: 1) - Chat ID associated with request"
}
```

### Response Schema

```json
{
  "success": "boolean",
  "message": "string",
  "results": [
    {
      "success": "boolean",
      "url": "string - S3 URL or local path to edited file",
      "error": "string (optional)",
      "index": "integer"
    }
  ],
  "request_id": "string"
}
```

### Notes

- All edits processed concurrently
- Images uploaded to S3: `edited/images/{request_id}/edit_{index}.jpg`
- Videos uploaded to S3: `edited/videos/{request_id}/edit_{index}.mp4`

### Example Request

```bash
curl -X POST "http://localhost:8000/v2/edit" \
  -H "Content-Type: application/json" \
  -d '{
    "urls": ["https://example.com/image.jpg"],
    "user_text": "Make the background more dramatic",
    "data_type": "image",
    "chat_id": "chat_123"
  }'
```

---

## 7. Regenerate

**Endpoint:** `POST /v2/regenerate`

**Description:** Regenerate images or videos based on user text instructions with variation (using random seeds).

### Request Schema

```json
{
  "urls": [
    "string - URL to regenerate (minimum 1 required)"
  ],
  "user_text": "string (required, min_length: 1) - User's text instruction for regeneration",
  "data_type": "string (required) - Type of data: 'image' or 'video'",
  "chat_id": "string (required, min_length: 1) - Chat ID associated with request"
}
```

### Response Schema

```json
{
  "success": "boolean",
  "request_id": "string",
  "data_type": "string",
  "total": "integer - Total number of items",
  "succeeded": "integer - Number of successful regenerations",
  "failed": "integer - Number of failed regenerations",
  "results": [
    {
      "success": "boolean",
      "url": "string - S3 URL or local path to regenerated file",
      "error": "string (optional)",
      "index": "integer",
      "seed_used": "integer - Random seed used for variation"
    }
  ]
}
```

### Notes

- All regenerations processed concurrently
- Random seed generated for each item (0 to 2^31 - 1)
- Images uploaded to S3: `regenerated/images/{request_id}/regenerate_{index}.jpg`
- Videos uploaded to S3: `regenerated/videos/{request_id}/regenerate_{index}.mp4`

### Example Request

```bash
curl -X POST "http://localhost:8000/v2/regenerate" \
  -H "Content-Type: application/json" \
  -d '{
    "urls": ["https://example.com/image.jpg"],
    "user_text": "Create a variation with more dramatic lighting",
    "data_type": "image",
    "chat_id": "chat_123"
  }'
```

---

## 8. Prompt Adaptation

**Endpoint:** `POST /v2/prompt-adaptation`

**Description:** Adapt existing scene prompts to feature a new product image while maintaining the same aesthetic.

### Request Schema

```json
{
  "product_image_url": "string (required) - URL or path to product image",
  "scene_prompts": [
    {
      "clip_index": "integer (optional) - Clip index (auto-generated if not provided)",
      "image_prompt": "string (required) - Image generation prompt",
      "video_prompt": "string (required) - Video generation prompt"
    }
  ]
}
```

### Response Schema

```json
{
  "success": "boolean",
  "message": "string",
  "adapted_prompts": [
    {
      "clip_index": "integer",
      "image_prompt": "string - Adapted image prompt with new product",
      "video_prompt": "string - Adapted video prompt with new product"
    }
  ]
}
```

### Notes

- Uses GPT-4 vision to analyze the new product
- Maintains exact aesthetic elements (lighting, mood, colors, style)
- Only changes product references to the new product
- Number of output prompts matches input

### Example Request

```bash
curl -X POST "http://localhost:8000/v2/prompt-adaptation" \
  -H "Content-Type: application/json" \
  -d '{
    "product_image_url": "https://example.com/new-product.jpg",
    "scene_prompts": [
      {
        "clip_index": 1,
        "image_prompt": "Red sneakers on white background with studio lighting",
        "video_prompt": "Camera slowly rotating around red sneakers"
      }
    ]
  }'
```

---

## 9. Fetch Template

**Endpoint:** `GET /v2/fetch-template/{template_id}`

**Description:** Retrieve a template from the database by its ID.

### Path Parameters

- `template_id`: string (required) - UUID of the template to fetch

### Response Schema

```json
{
  "id": "string - Template UUID",
  "name": "string - Template name",
  "config": {
    "name": "string",
    "clips": [
      {
        "index": "integer",
        "duration": "float - Duration in seconds",
        "required": "boolean"
      }
    ],
    "logo_outro": "boolean",
    "music_file": "string (optional) - Music file path or URL",
    "transitions": [
      {
        "type": "string - Transition type (e.g., 'cut', 'crossfade')",
        "duration": "float - Duration in seconds",
        "between_clips": ["integer - List of clip indices"]
      }
    ],
    "fade_in_duration": "float - Fade in duration in seconds",
    "fade_out_duration": "float - Fade out duration in seconds",
    "logo_file": "string (optional) - Logo file path or URL"
  },
  "created_at": "datetime - Template creation timestamp",
  "updated_at": "datetime - Template last update timestamp",
  "moodboard_data": [
    {
      "clip_index": "integer",
      "image_prompt": "string",
      "video_prompt": "string"
    }
  ]
}
```

### Example Request

```bash
curl -X GET "http://localhost:8000/v2/fetch-template/76d7ee3a-3633-4a87-a29e-90b33eb6189b"
```

---

## Common Error Responses

All endpoints may return the following error responses:

### 400 Bad Request
```json
{
  "detail": "Validation error message"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Error message describing what went wrong"
}
```

### 503 Service Unavailable
```json
{
  "detail": "Service unavailable: API_KEY not configured"
}
```

---

## Environment Variables Required

```bash
# Required for Creative Analysis & Prompt Adaptation
OPENAI_API_KEY=your_openai_api_key

# Required for Image & Video Generation, Edit, Regenerate
REPLICATE_API_TOKEN=your_replicate_api_token

# Required for Auto Stitch
GEMINI_API_KEY=your_gemini_api_key

# Required for Storage (S3/Supabase)
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_ROLE_KEY=your_supabase_key
# OR
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
AWS_S3_BUCKET=your_bucket_name
AWS_REGION=your_region
```

---

## API Flow: Complete Video Generation Pipeline

### Recommended Flow

```
1. Creative Analysis (Generate prompts)
   POST /v2/creative-analysis
   ↓
2. Image Generation (Generate images from prompts)
   POST /v2/image-generation
   ↓
3. Clip Generation (Generate video clips from images)
   POST /v2/clip-generation
   ↓
4. Auto Stitch OR Manual Stitch (Combine clips into final video)
   POST /v2/auto-stitch
   OR
   POST /v2/manual-stitch
```

### Alternative Flow: Using Existing Templates

```
1. Fetch Template
   GET /v2/fetch-template/{template_id}
   ↓
2. Prompt Adaptation (Adapt template prompts to new product)
   POST /v2/prompt-adaptation
   ↓
3. Image Generation
   POST /v2/image-generation
   ↓
4. Clip Generation
   POST /v2/clip-generation
   ↓
5. Manual Stitch (Using template config)
   POST /v2/manual-stitch
```

### Iterative Refinement Flow

```
Generate Content → Review → Edit/Regenerate → Final Stitch

POST /v2/creative-analysis
POST /v2/image-generation
POST /v2/clip-generation
↓
If refinement needed:
  POST /v2/edit (for targeted edits)
  OR
  POST /v2/regenerate (for variations)
↓
POST /v2/auto-stitch or /v2/manual-stitch
```

---

## Rate Limits & Performance

- **Concurrent Processing**: Image generation, clip generation, edit, and regenerate endpoints process items concurrently for better performance
- **Retry Logic**: Image generation includes automatic retry (up to 3 attempts)
- **File Size Limits**: Depend on underlying services (Replicate, Supabase/S3)
- **Timeout**: Long-running operations (video generation, stitching) may take several minutes

---

## Notes

1. All file inputs accept either URLs or local file paths
2. Outputs are automatically uploaded to S3/Supabase storage when available
3. Local fallback paths are provided if storage upload fails
4. All timestamps are in ISO 8601 format
5. UUIDs are used for request tracking and organization
6. The API is async/await based for optimal performance

