import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.core.database import Base


SAMPLE_XML_INVOICE = """<?xml version="1.0" encoding="UTF-8"?>
<HDon>
  <DLHDon Id="data">
    <TTChung>
      <KHMSHDon>1</KHMSHDon>
      <KHHDon>1C24TKK</KHHDon>
      <SHDon>00001234</SHDon>
      <NLap>2026-09-28</NLap>
      <DVTTe>VND</DVTTe>
      <TGia>1</TGia>
      <HTTToan>TM/CK</HTTToan>
      <MCCQT>TCT-123456789</MCCQT>
    </TTChung>
    <NDHDon>
      <NBan>
        <Ten>CONG TY TNHH CONG NGHE ABC VIET NAM</Ten>
        <MST>0100109106</MST>
        <DChi>So 123 Pho Hue, Quan Hai Ba Trung, Ha Noi</DChi>
        <SDThoai>02438888888</SDThoai>
        <STKNHang>19020000000001</STKNHang>
        <TNHang>Techcombank</TNHang>
      </NBan>
      <NMua>
        <Ten>CONG TY CO PHAN PHAN MEM KHOA HOC</Ten>
        <MST>0312345678</MST>
        <DChi>Quan 1, TP Ho Chi Minh</DChi>
      </NMua>
      <DSHHDVu>
        <HHDVu>
          <STT>1</STT>
          <THHDVu>May tinh xach tay Dell Latitude</THHDVu>
          <DVTinh>Cai</DVTinh>
          <SLuong>2</SLuong>
          <DGia>25000000</DGia>
          <STCKhau>0</STCKhau>
          <ThTien>50000000</ThTien>
          <TSuat>10%</TSuat>
        </HHDVu>
      </DSHHDVu>
      <TToan>
        <TgTCThue>50000000</TgTCThue>
        <TgTThue>5000000</TgTThue>
        <TgTTTBSo>55000000</TgTTTBSo>
        <TgTTTBChu>Nam muoi lam trieu dong</TgTTTBChu>
      </TToan>
    </NDHDon>
  </DLHDon>
  <DSCKS>
    <Signature xmlns="http://www.w3.org/2000/09/xmldsig#">
      <SignedInfo>
        <CanonicalizationMethod Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"/>
        <SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"/>
      </SignedInfo>
      <SignatureValue>MOCK_SIGNATURE_VALUE</SignatureValue>
      <KeyInfo>
        <X509Data>
          <X509Certificate>MOCK_BASE64_CERTIFICATE</X509Certificate>
        </X509Data>
      </KeyInfo>
    </Signature>
  </DSCKS>
</HDon>
"""


@pytest.fixture
def sample_xml_bytes() -> bytes:
    return SAMPLE_XML_INVOICE.encode("utf-8")


@pytest.fixture
def sample_pdf_bytes() -> bytes:
    import io
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (800, 1000), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    d.text((50, 50), "HOA DON GIA TRI GIA TANG", fill=(0, 0, 0))
    d.text((50, 100), "So hoa don: 0001234", fill=(0, 0, 0))
    d.line([(50, 150), (750, 150)], fill=(0, 0, 0), width=2)
    buf = io.BytesIO()
    img.save(buf, format="PDF")
    return buf.getvalue()


@pytest.fixture
def sample_image_bytes() -> bytes:
    import io
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (800, 1000), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    d.text((50, 50), "HOA DON GIA TRI GIA TANG", fill=(0, 0, 0))
    d.text((50, 100), "So hoa don: 0001234", fill=(0, 0, 0))
    d.line([(50, 150), (750, 150)], fill=(0, 0, 0), width=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()
