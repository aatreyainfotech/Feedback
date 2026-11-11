// menuSpace: on phones keep the right side free for the admin / officer menu button.
const Header = ({ logo, menuSpace = false }) => {
  return (
    <header className={`bg-white shadow-md py-3 px-4 sm:py-4 sm:px-6 ${menuSpace ? 'pr-16 md:pr-6' : ''} border-b-4 border-[#0EA854]`}>
      <div className="max-w-7xl mx-auto flex items-center justify-center gap-3 sm:gap-4">
        <img 
          src={logo}
          alt="Telangana Government"
          className="h-12 w-12 sm:h-16 sm:w-16 shrink-0 object-contain"
        />
        <div className="text-center">
          <h1 className="text-lg leading-tight sm:text-3xl font-bold text-[#0EA854]">
            Government of Telangana
          </h1>
          <p className="text-sm sm:text-xl text-[#721C24] font-semibold">
            Endowment Department
          </p>
        </div>
      </div>
    </header>
  );
};

export default Header;