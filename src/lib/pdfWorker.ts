// @ts-ignore - pdfjs-dist build path lacks type declarations in some setups
import { GlobalWorkerOptions } from 'pdfjs-dist/build/pdf';
// In Vite, importing the worker with ?url returns a URL string we can assign
// to the pdf.js GlobalWorkerOptions.
// This avoids relying on a CDN and fixes 404/fake worker errors.
// Make sure pdfjs-dist is installed in your frontend project.
// npm i pdfjs-dist
// or
// yarn add pdfjs-dist
// @ts-ignore - importing worker asset URL for Vite bundler
import workerSrc from 'pdfjs-dist/build/pdf.worker.min.mjs?url';

GlobalWorkerOptions.workerSrc = workerSrc as unknown as string;


