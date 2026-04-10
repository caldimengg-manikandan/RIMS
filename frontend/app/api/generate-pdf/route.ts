import { NextRequest, NextResponse } from "next/server"
import puppeteer from "puppeteer"

export async function POST(req: NextRequest) {
  let browser = null
  try {
    const { html } = await req.json()

    if (!html) {
      return NextResponse.json({ error: "No HTML content provided" }, { status: 400 })
    }

    // Launch puppeteer
    browser = await puppeteer.launch({
      args: ["--no-sandbox", "--disable-setuid-sandbox", "--font-render-hinting=none"],
      headless: true,
    })

    const page = await browser.newPage()

    // Set viewport to A4 dimensions at 96 DPI for layout calculation
    await page.setViewport({
      width: 794,
      height: 1123,
      deviceScaleFactor: 2, // Higher scale factor for better quality rendering (shadows, paths)
    })

    // Inject necessary CSS adjustments for A4 printing
    const styledHtml = `
      <style>
        @page {
          size: A4;
          margin: 0;
        }
        body {
          margin: 0;
          -webkit-print-color-adjust: exact !important;
          print-color-adjust: exact !important;
        }
        * {
          -webkit-print-color-adjust: exact !important;
          print-color-adjust: exact !important;
        }
      </style>
      ${html}
    `

    // Set content and wait for network to be idle (important for fonts/images from external URLs)
    await page.setContent(styledHtml, {
      waitUntil: "networkidle0",
    })

    // Generate PDF
    const pdfBuffer = await page.pdf({
      format: "A4",
      printBackground: true,
      margin: {
        top: "0px",
        right: "0px",
        bottom: "0px",
        left: "0px",
      },
      preferCSSPageSize: true,
    })

    await browser.close()

    // Return the PDF as response
    return new NextResponse(pdfBuffer, {
      status: 200,
      headers: {
        "Content-Type": "application/pdf",
        "Content-Disposition": 'attachment; filename="offer-letter.pdf"',
        "Content-Length": pdfBuffer.length.toString(),
      },
    })
  } catch (error: any) {
    console.error("PDF Generation Error:", error)
    if (browser) await (browser as any).close()
    return NextResponse.json({ error: `Failed to generate PDF: ${error.message}` }, { status: 500 })
  }
}
