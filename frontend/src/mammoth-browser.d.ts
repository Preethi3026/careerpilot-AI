declare module "mammoth/mammoth.browser" {
  type ExtractedText = { value: string; messages: unknown[] };
  const mammoth: {
    extractRawText(input: { arrayBuffer: ArrayBuffer }): Promise<ExtractedText>;
  };
  export default mammoth;
}
