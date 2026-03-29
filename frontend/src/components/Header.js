const Header = ({ logo }) => {
  return (
    <header className="bg-white shadow-md py-4 px-6 border-b-4 border-[#0EA854]">
      <div className="max-w-7xl mx-auto flex items-center justify-center gap-4">
        <img 
          src={logo}
          alt="Telangana Government"
          className="h-16 w-16 object-contain"
        />
        <div className="text-center">
          <h1 className="text-2xl sm:text-3xl font-bold text-[#0EA854]">
            Government of Telangana
          </h1>
          <p className="text-lg sm:text-xl text-[#721C24] font-semibold">
            Endowment Department
          </p>
        </div>
      </div>
    </header>
  );
};

export default Header;