const Footer = () => {
  return (
    <footer className="relative">
      {/* Magic Curve */}
      <div className="h-8 bg-gradient-to-r from-[#721C24] to-[#4A1016] rounded-t-[2rem]"></div>
      
      {/* Footer Content */}
      <div className="bg-gradient-to-r from-[#721C24] to-[#4A1016] text-white py-4 px-6">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-2">
          <p className="text-sm">
            Sponsored by <span className="text-[#F4C430] font-bold">Central Bank of India</span>
          </p>
          <p className="text-xs text-white/70">
            © {new Date().getFullYear()} Telangana Endowment Department. All rights reserved.
          </p>
          <p className="text-sm">
            Developed by <span className="text-[#F4C430] font-bold">Aatreya Infotech</span>
          </p>
        </div>
      </div>
    </footer>
  );
};

export default Footer;